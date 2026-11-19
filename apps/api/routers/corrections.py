"""
apps/api/routers/corrections.py

POST /projects/{id}/corrections   — elektricien stuurt correctie in
GET  /projects/{id}/corrections   — geeft alle correcties voor een project
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.database import get_db
from apps.api.models.db import CorrectionRow, ProjectRow
from packages.schema import Correction, CorrectionAction, SymbolType

router = APIRouter()


class CorrectionCreate(BaseModel):
    action: CorrectionAction
    symbol_id: str | None = None
    new_type: SymbolType | None = None
    new_x: float | None = None
    new_y: float | None = None
    comment: str = ""


class CorrectionResponse(BaseModel):
    id: str
    project_id: str
    action: CorrectionAction
    symbol_id: str | None
    new_type: SymbolType | None
    new_x: float | None
    new_y: float | None
    comment: str
    created_at: str


def _row_to_response(row: CorrectionRow) -> CorrectionResponse:
    return CorrectionResponse(
        id=row.id,
        project_id=row.project_id,
        action=CorrectionAction(row.action),
        symbol_id=row.symbol_id,
        new_type=SymbolType(row.new_type) if row.new_type else None,
        new_x=row.new_x,
        new_y=row.new_y,
        comment=row.comment,
        created_at=row.created_at.isoformat(),
    )


@router.post(
    "/{project_id}/corrections",
    status_code=status.HTTP_201_CREATED,
    response_model=CorrectionResponse,
)
async def add_correction(
    project_id: str,
    body: CorrectionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Slaat een correctie van de elektricien op als trainingsdata.

    - `action=add`         — nieuw symbool toevoegen (geef new_type + new_x/y)
    - `action=remove`      — bestaand symbool verwijderen (geef symbol_id)
    - `action=change_type` — type aanpassen (geef symbol_id + new_type)
    - `action=move`        — positie aanpassen (geef symbol_id + new_x/y)
    """
    project = await db.get(ProjectRow, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")

    # Basisvalidatie
    if body.action == CorrectionAction.ADD and (
        body.new_type is None or body.new_x is None or body.new_y is None
    ):
        raise HTTPException(
            status_code=422,
            detail="Bij action=add zijn new_type, new_x en new_y verplicht.",
        )
    if body.action in (
        CorrectionAction.REMOVE,
        CorrectionAction.CHANGE_TYPE,
        CorrectionAction.MOVE,
    ) and not body.symbol_id:
        raise HTTPException(
            status_code=422,
            detail=f"Bij action={body.action} is symbol_id verplicht.",
        )

    row = CorrectionRow(
        project_id=project_id,
        action=body.action.value,
        symbol_id=body.symbol_id,
        new_type=body.new_type.value if body.new_type else None,
        new_x=body.new_x,
        new_y=body.new_y,
        comment=body.comment,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _row_to_response(row)


@router.get("/{project_id}/corrections", response_model=list[CorrectionResponse])
async def list_corrections(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Geeft alle correcties voor een project terug (voor review-UI en training)."""
    project = await db.get(ProjectRow, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")

    result = await db.execute(
        select(CorrectionRow)
        .where(CorrectionRow.project_id == project_id)
        .order_by(CorrectionRow.created_at.asc())
    )
    rows = result.scalars().all()
    return [_row_to_response(r) for r in rows]
