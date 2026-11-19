from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.database import get_db
from apps.api.review_projects import reviewed_symbols
from apps.shared.models import InstallationCheckRow, ProjectRow
from packages.schema import ProjectStatus, Symbol

router = APIRouter(prefix="/projects/{project_id}/installation")
Database = Annotated[AsyncSession, Depends(get_db)]


class InstallationItem(BaseModel):
    symbol: Symbol
    room: str | None
    installed: bool


class CheckUpdate(BaseModel):
    installed: bool


async def _finished_project(db: AsyncSession, project_id: str, *, lock: bool = False):
    row = await db.get(ProjectRow, project_id, with_for_update=lock)
    if row is None:
        raise HTTPException(404, "Project niet gevonden.")
    if row.status != ProjectStatus.DONE.value:
        raise HTTPException(409, "De analyse is nog niet afgerond.")
    return row


@router.get("")
async def checklist(project_id: str, db: Database) -> list[InstallationItem]:
    row = await _finished_project(db, project_id)
    installed = set(await db.scalars(
        select(InstallationCheckRow.symbol_id).where(InstallationCheckRow.project_id == project_id)
    ))
    rooms = {room["id"]: room["name"] for room in row.rooms or []}
    return [
        InstallationItem(symbol=symbol, room=rooms.get(symbol.room_id), installed=symbol.id in installed)
        for symbol in await reviewed_symbols(db, row)
    ]


@router.put("/{symbol_id}", status_code=204)
async def update_check(project_id: str, symbol_id: str, body: CheckUpdate, db: Database) -> Response:
    row = await _finished_project(db, project_id, lock=True)
    if not any(symbol.id == symbol_id for symbol in await reviewed_symbols(db, row)):
        raise HTTPException(404, "Symbool niet gevonden in de beoordeelde tekening.")
    existing = await db.get(InstallationCheckRow, (project_id, symbol_id))
    if body.installed and existing is None:
        db.add(InstallationCheckRow(project_id=project_id, symbol_id=symbol_id))
    elif not body.installed and existing is not None:
        await db.delete(existing)
    await db.commit()
    return Response(status_code=204)
