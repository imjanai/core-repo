"""
apps/api/routers/materials.py

GET  /projects/{id}/materials           — JSON materiaallijst
GET  /projects/{id}/materials?format=xlsx — Excel-download
GET  /projects/{id}/materials?format=pdf  — PDF-offerte
"""

import io
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.database import get_db
from apps.api.review_projects import reviewed_symbols
from apps.shared.models import ProjectRow
from packages.materials import compute_materials
from packages.materials.exports import build_materials_pdf, build_materials_xlsx
from packages.schema import MaterialLine, Project, ProjectStatus

router = APIRouter()


class MaterialsResponse(BaseModel):
    project_id: str
    total_price: float | None
    currency: str = "EUR"
    items: list[MaterialLine]


@router.get("/{project_id}/materials")
async def get_materials(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    review: bool = False,
    fmt: Literal["json", "xlsx", "pdf"] = Query("json", alias="format"),
):
    """
    Geeft de materiaallijst terug.

    - `format=json`  → JSON (standaard)
    - `format=xlsx`  → Excel-download
    - `format=pdf`   → PDF-offerte
    """
    row = await db.get(ProjectRow, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")
    if ProjectStatus(row.status) not in (ProjectStatus.DONE,):
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline nog niet klaar (status: {row.status}).",
        )

    if review:
        project = Project(
            id=row.id, name=row.name, symbols=await reviewed_symbols(db, row),
            rooms=row.rooms or [], meta=row.meta or {}, scale=row.scale,
        )
        items = compute_materials(project).materials
    else:
        items = [MaterialLine(**m) for m in (row.materials or [])]
    total = (
        sum(m.total_price for m in items if m.total_price is not None)
        if items
        else None
    )

    if fmt == "json":
        return MaterialsResponse(
            project_id=project_id, total_price=total, items=items
        )

    if fmt == "xlsx":
        xlsx_bytes = build_materials_xlsx(items)
        return StreamingResponse(
            io.BytesIO(xlsx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="materiaal_{project_id}.xlsx"'
            },
        )

    if fmt == "pdf":
        pdf_bytes = build_materials_pdf(items, project_id, total)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="offerte_{project_id}.pdf"'
            },
        )
