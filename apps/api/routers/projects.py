import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.config import settings
from apps.api.core.database import get_db
from apps.api.core.storage import upload_file, generate_presigned_url
from apps.api.models.db import ProjectRow
from apps.api.tasks import run_pipeline
from packages.schema import FileType, Project, ProjectStatus

router = APIRouter()


# ---------------------------------------------------------------------------
# Hulpfuncties
# ---------------------------------------------------------------------------


def _detect_file_type(filename: str) -> FileType:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mapping = {
        "dxf": FileType.DXF,
        "ifc": FileType.IFC,
        "pdf": FileType.PDF,
        "png": FileType.IMAGE,
        "jpg": FileType.IMAGE,
        "jpeg": FileType.IMAGE,
        "tif": FileType.IMAGE,
        "tiff": FileType.IMAGE,
    }
    return mapping.get(ext, FileType.UNKNOWN)


def _row_to_project(row: ProjectRow) -> Project:
    return Project(
        id=row.id,
        name=row.name,
        status=ProjectStatus(row.status),
        file_type=FileType(row.file_type),
        scale=row.scale,
        rooms=row.rooms or [],
        symbols=row.symbols or [],
        materials=row.materials or [],
        warnings=row.warnings or [],
        meta=row.meta or {},
    )


# ---------------------------------------------------------------------------
# Request / response schema's
# ---------------------------------------------------------------------------


class ProjectSummary(BaseModel):
    id: str
    name: str
    status: ProjectStatus
    file_type: FileType
    created_at: str
    download_url: str | None = None


class ProjectListResponse(BaseModel):
    items: list[ProjectSummary]
    total: int
    page: int
    page_size: int


class PipelineStatusResponse(BaseModel):
    project_id: str
    status: ProjectStatus
    task_id: str | None
    symbol_count: int
    warning_count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=Project)
async def create_project(
    file: Annotated[UploadFile, File(description="DXF, IFC, PDF of afbeelding")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Upload een tekening en start de analysepipeline."""
    if file.size and file.size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Bestand te groot (max {settings.max_upload_bytes // (1024*1024)} MB).",
        )

    data = await file.read()
    s3_key = await upload_file(data, file.filename or "upload")

    project_id = str(uuid.uuid4())
    file_type = _detect_file_type(file.filename or "")

    row = ProjectRow(
        id=project_id,
        name=file.filename or "",
        status=ProjectStatus.UPLOADED.value,
        file_type=file_type.value,
        original_filename=file.filename or "",
        s3_key=s3_key,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    # Start de Celery-pipelinetaak asynchroon.
    task = run_pipeline.delay(project_id, s3_key, file_type.value)
    row.task_id = task.id
    row.status = ProjectStatus.PROCESSING.value
    await db.commit()
    await db.refresh(row)

    return _row_to_project(row)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Geeft een gepagineerde lijst van alle projecten, nieuwste eerst."""
    offset = (page - 1) * page_size

    total_result = await db.execute(select(func.count()).select_from(ProjectRow))
    total: int = total_result.scalar_one()

    rows_result = await db.execute(
        select(ProjectRow)
        .order_by(ProjectRow.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = rows_result.scalars().all()

    items: list[ProjectSummary] = []
    for row in rows:
        url = None
        if row.s3_key:
            url = await generate_presigned_url(row.s3_key)
        items.append(
            ProjectSummary(
                id=row.id,
                name=row.name,
                status=ProjectStatus(row.status),
                file_type=FileType(row.file_type),
                created_at=row.created_at.isoformat(),
                download_url=url,
            )
        )

    return ProjectListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Geeft het volledige projectmodel terug (symbolen, ruimtes, materialen)."""
    row = await db.get(ProjectRow, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")
    return _row_to_project(row)


@router.get("/{project_id}/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Pollt de status van de lopende analysepipeline."""
    row = await db.get(ProjectRow, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")

    return PipelineStatusResponse(
        project_id=row.id,
        status=ProjectStatus(row.status),
        task_id=row.task_id,
        symbol_count=len(row.symbols or []),
        warning_count=len(row.warnings or []),
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Verwijdert een project (inclusief DB-record; S3-object blijft voor audit)."""
    row = await db.get(ProjectRow, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")
    await db.delete(row)
    await db.commit()
