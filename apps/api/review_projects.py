from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.shared.models import CorrectionRow, ProjectRow
from packages.materials import compute_materials
from packages.schema import Correction, MaterialLine, Project, Symbol
from packages.schema.review import apply_corrections


async def project_corrections(db: AsyncSession, project_id: str) -> list[CorrectionRow]:
    result = await db.scalars(
        select(CorrectionRow)
        .where(CorrectionRow.project_id == project_id)
        .order_by(CorrectionRow.created_at, CorrectionRow.id)
    )
    return list(result)


async def reviewed_symbols(db: AsyncSession, row: ProjectRow) -> list[Symbol]:
    corrections = await project_corrections(db, row.id)
    return apply_corrections(
        (Symbol.model_validate(symbol) for symbol in row.symbols or []),
        (Correction.model_validate(item, from_attributes=True) for item in corrections),
    )


async def reviewed_materials(db: AsyncSession, row: ProjectRow) -> list[MaterialLine]:
    project = Project(
        id=row.id, name=row.name, symbols=await reviewed_symbols(db, row),
        rooms=row.rooms or [], meta=row.meta or {}, scale=row.scale,
    )
    return compute_materials(project).materials
