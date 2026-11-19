from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.database import get_db
from apps.api.review_projects import project_corrections, reviewed_symbols
from apps.shared.models import CorrectionRow, ProjectRow
from packages.materials import compute_materials
from packages.schema import CorrectionAction, FileType, Project, ProjectStatus, Symbol
from packages.schema.revisions import (
    MaterialChange, SymbolChange, compare_materials, compare_symbols, match_symbols,
)

router = APIRouter(prefix="/projects/{project_id}/review")


class RevisionComparison(BaseModel):
    previous_name: str
    changes: list[SymbolChange]
    materials: list[MaterialChange]


class CarryResult(BaseModel):
    applied: int
    already_reviewed: int
    needs_review: list[Symbol]


async def _projects(db: AsyncSession, current_id: str, previous_id: str, *, lock: bool = False):
    if current_id == previous_id:
        raise HTTPException(422, "Kies twee verschillende DXF-projecten.")
    previous = await db.get(ProjectRow, previous_id)
    current = await db.get(ProjectRow, current_id, with_for_update=lock)
    if previous is None or current is None:
        raise HTTPException(404, "Eén van de projecten bestaat niet meer.")
    if any(row.file_type != FileType.DXF.value for row in (previous, current)):
        raise HTTPException(422, "Kies twee DXF-projecten.")
    if any(row.status != ProjectStatus.DONE.value for row in (previous, current)):
        raise HTTPException(409, "Beide analyses moeten afgerond zijn.")
    return previous, current


@router.get("/revision", response_model=RevisionComparison)
async def revision(
    project_id: str, previous_id: str, db: Annotated[AsyncSession, Depends(get_db)],
):
    previous, current = await _projects(db, project_id, previous_id)
    before, after = await reviewed_symbols(db, previous), await reviewed_symbols(db, current)
    return RevisionComparison(
        previous_name=previous.name,
        changes=compare_symbols(before, after),
        materials=compare_materials(
            compute_materials(Project(id=previous.id, symbols=before)).materials,
            compute_materials(Project(id=current.id, symbols=after)).materials,
        ),
    )


@router.post("/revision/carry", response_model=CarryResult)
async def carry(
    project_id: str, previous_id: str, db: Annotated[AsyncSession, Depends(get_db)],
):
    previous, current = await _projects(db, project_id, previous_id, lock=True)
    before_raw = [Symbol.model_validate(item) for item in previous.symbols or []]
    after_raw = [Symbol.model_validate(item) for item in current.symbols or []]
    original_ids = {symbol.id for symbol in before_raw}
    before_reviewed = {symbol.id: symbol for symbol in await reviewed_symbols(db, previous)}
    current_corrections = await project_corrections(db, current.id)
    touched = {item.symbol_id for item in current_corrections}

    matches, _, _ = match_symbols(before_raw, after_raw, distance=0)
    result = CarryResult(applied=0, already_reviewed=0, needs_review=[])
    result.needs_review.extend(item for key, item in before_reviewed.items() if key not in original_ids)
    controlled = ("block_name", "layer")
    for old in before_raw:
        corrected = before_reviewed.get(old.id)
        if corrected and (corrected.type, corrected.x, corrected.y) == (old.type, old.x, old.y):
            continue
        target = matches.get(old.id)
        same_block = target is not None and all(
            old.attributes.get(key) and target.attributes.get(key) == old.attributes[key]
            for key in controlled
        )
        if target is None or target.type != old.type or not same_block:
            result.needs_review.append(corrected or old)
            continue
        if target.id in touched:
            result.already_reviewed += 1
            continue
        correction = CorrectionRow(
            project_id=current.id, symbol_id=target.id, comment="Overgenomen uit vorige revisie.",
        )
        if corrected is None:
            correction.action = CorrectionAction.REMOVE.value
        else:
            correction.action = CorrectionAction.CHANGE_TYPE.value
            correction.new_type = corrected.type.value
            if (corrected.x, corrected.y) != (old.x, old.y):
                correction.new_x = target.x + corrected.x - old.x
                correction.new_y = target.y + corrected.y - old.y
        db.add(correction)
        result.applied += 1
    await db.commit()
    return result
