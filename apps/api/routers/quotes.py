from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.database import get_db
from apps.api.review_projects import reviewed_materials
from apps.shared.models import ProjectRow, QuoteRow
from packages.materials.quote_pdf import render_quote_pdf
from packages.materials.quotes import Quote, QuoteInput, QuoteMaterial, quote_materials
from packages.schema import ProjectStatus

router = APIRouter()
Database = Annotated[AsyncSession, Depends(get_db)]


async def _quote(db: AsyncSession, quote_id: str) -> Quote:
    row = await db.get(QuoteRow, quote_id)
    if row is None:
        raise HTTPException(404, "Offerte niet gevonden.")
    return _snapshot(row)


def _snapshot(row: QuoteRow) -> Quote:
    return Quote(id=row.id, project_id=row.project_id, created_at=row.created_at, **row.snapshot)


@router.get("/projects/{project_id}/quotes")
async def list_quotes(project_id: str, db: Database) -> list[Quote]:
    rows = await db.scalars(
        select(QuoteRow).where(QuoteRow.project_id == project_id)
        .order_by(QuoteRow.created_at.desc(), QuoteRow.id.desc())
    )
    return [_snapshot(row) for row in rows]


@router.get("/projects/{project_id}/quotes/draft")
async def draft_quote(project_id: str, db: Database) -> list[QuoteMaterial]:
    row = await db.get(ProjectRow, project_id)
    if row is None:
        raise HTTPException(404, "Project niet gevonden.")
    if row.status != ProjectStatus.DONE.value:
        raise HTTPException(409, "De analyse is nog niet afgerond.")
    return quote_materials(await reviewed_materials(db, row))


@router.post("/projects/{project_id}/quotes", status_code=201)
async def save_quote(project_id: str, body: QuoteInput, db: Database) -> Quote:
    row = await db.get(ProjectRow, project_id, with_for_update=True)
    if row is None:
        raise HTTPException(404, "Project niet gevonden.")
    if row.status != ProjectStatus.DONE.value:
        raise HTTPException(409, "De analyse is nog niet afgerond.")
    expected = {item.key: item.quantity for item in quote_materials(await reviewed_materials(db, row))}
    actual = {item.key: item.quantity for item in body.materials}
    if actual != expected or len(actual) != len(body.materials):
        raise HTTPException(409, "De materiaallijst is gewijzigd. Vernieuw de review voordat je de offerte opslaat.")
    if any(item.unit_price is None for item in body.materials):
        raise HTTPException(422, "Vul een prijs in voor elk materiaal.")
    quote = QuoteRow(
        project_id=project_id,
        snapshot={**body.model_dump(mode="json"), "project_name": row.name},
    )
    db.add(quote)
    await db.commit()
    await db.refresh(quote)
    return _snapshot(quote)


@router.get("/quotes/{quote_id}/pdf")
async def quote_pdf(quote_id: str, db: Database, baseline: str | None = None) -> Response:
    quote = await _quote(db, quote_id)
    previous = await _quote(db, baseline) if baseline else None
    if previous and previous.id == quote.id:
        raise HTTPException(422, "Kies twee verschillende offerteversies.")
    pdf = await run_in_threadpool(render_quote_pdf, quote, previous)
    filename = "meerwerk" if previous else "offerte"
    return Response(pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{filename}-{quote.id}.pdf"',
    })
