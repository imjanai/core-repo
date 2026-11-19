from typing import Annotated

import ezdxf
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.database import get_db
from apps.api.core.storage import download_file
from apps.api.review_projects import reviewed_symbols
from apps.shared.models import ProjectRow
from packages.parsers.dxf_preview import preview_paths
from packages.schema import FileType, ProjectStatus, Symbol, SymbolType

router = APIRouter()


class DrawingPreview(BaseModel):
    paths: list[list[tuple[float, float]]]
    truncated: bool


@router.get("/review/symbol-types")
async def symbol_types() -> list[SymbolType]:
    return list(SymbolType)


@router.get("/projects/{project_id}/review/symbols")
async def symbols(
    project_id: str, db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Symbol]:
    row = await db.get(ProjectRow, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")
    if row.status != ProjectStatus.DONE.value:
        raise HTTPException(status_code=409, detail="De analyse is nog niet klaar.")
    return await reviewed_symbols(db, row)


@router.get("/projects/{project_id}/review/drawing")
async def drawing(
    project_id: str, db: Annotated[AsyncSession, Depends(get_db)],
) -> DrawingPreview:
    row = await db.get(ProjectRow, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")
    if row.file_type != FileType.DXF.value or not row.s3_key:
        raise HTTPException(status_code=422, detail="Voor dit project is geen DXF beschikbaar.")
    try:
        data = await download_file(row.s3_key)
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=502, detail="De bronbestanden zijn niet bereikbaar.") from exc
    try:
        paths, truncated = await run_in_threadpool(preview_paths, data)
    except (ezdxf.DXFError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="De DXF kon niet worden weergegeven.") from exc
    return DrawingPreview(paths=paths, truncated=truncated)
