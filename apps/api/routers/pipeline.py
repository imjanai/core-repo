"""
apps/api/routers/pipeline.py — voortgang en herstel van de analyse.

De review-UI pollt `GET /projects/{id}/pipeline` en ziet per stap hoeveel
pogingen nodig waren, hoe lang die duurde en waarom iets is overgeslagen.
`POST .../pipeline/resume` geeft de elektricien (of een operator) een
knop om een mislukte analyse opnieuw te starten zónder opnieuw te uploaden.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.shared.config import settings
from apps.api.core.database import get_db
from apps.shared.models import PipelineRunRow, row_to_run
from apps.api.pipeline_dispatch import resume_pipeline
from packages.pipeline import RunState

router = APIRouter()


# ---------------------------------------------------------------------------
# Response-modellen
# ---------------------------------------------------------------------------


class StageProgress(BaseModel):
    stage_id: str
    name: str
    state: str
    attempts: int = 0
    duration_ms: int = 0
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class PipelineRunDetail(BaseModel):
    run_id: str
    project_id: str
    pipeline: str
    state: RunState
    progress: float
    current_stage: str | None = None
    error: str | None = None
    stages: list[StageProgress]
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime


class PipelineRunList(BaseModel):
    items: list[PipelineRunDetail]


class ResumeResponse(BaseModel):
    run_id: str
    task_id: str | None = None
    state: str = "queued"


# ---------------------------------------------------------------------------
# Hulpjes
# ---------------------------------------------------------------------------


async def _latest_run(db: AsyncSession, project_id: str) -> PipelineRunRow | None:
    result = await db.execute(
        select(PipelineRunRow)
        .where(PipelineRunRow.project_id == project_id)
        .order_by(PipelineRunRow.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _detail(row: PipelineRunRow) -> PipelineRunDetail:
    run = row_to_run(row)
    return PipelineRunDetail(
        run_id=run.run_id,
        project_id=run.project_id,
        pipeline=run.pipeline,
        state=run.state,
        progress=run.progress,
        current_stage=run.current_stage,
        error=run.error,
        stages=[
            StageProgress(
                stage_id=s.stage_id,
                name=s.name,
                state=s.state.value,
                attempts=s.attempts,
                duration_ms=s.duration_ms,
                error=s.error,
                started_at=s.started_at,
                finished_at=s.finished_at,
            )
            for s in run.stages
        ],
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        updated_at=run.updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/{project_id}/pipeline", response_model=PipelineRunDetail)
async def get_pipeline_detail(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Live voortgang van de laatste analyse: staat, huidige stap, alle stappen."""
    row = await _latest_run(db, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Nog geen pipeline-run voor dit project.")
    return _detail(row)


@router.get("/{project_id}/pipeline/runs", response_model=PipelineRunList)
async def list_pipeline_runs(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20,
):
    """Runhistorie — bruikbaar voor audits en om te zien wat er misging."""
    rows = (
        await db.execute(
            select(PipelineRunRow)
            .where(PipelineRunRow.project_id == project_id)
            .order_by(PipelineRunRow.created_at.desc())
            .limit(max(1, min(limit, 100)))
        )
    ).scalars().all()
    return PipelineRunList(items=[_detail(r) for r in rows])


@router.post("/{project_id}/pipeline/resume", status_code=status.HTTP_202_ACCEPTED,
             response_model=ResumeResponse)
async def resume_pipeline_run(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Hervat de laatste run bij de eerste stap die niet klaar was.

    * geslaagd  → 409 (niets te doen)
    * loopt     → 409, tenzij de run al langer dan `stale_after_minutes`
                  niet bijgewerkt is (dan is de worker waarschijnlijk
                  verdwenen en is hervatten precies wat we willen)
    * gefaald/geannuleerd → 202, taak in de wachtrij
    """
    row = await _latest_run(db, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Nog geen pipeline-run voor dit project.")

    run = row_to_run(row)

    if run.state == RunState.SUCCEEDED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="De laatste analyse is al voltooid; upload opnieuw om te heranalyseren.",
        )

    stale_cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=settings.stale_after_minutes
    )
    in_progress = run.state in {RunState.PENDING, RunState.RUNNING}
    looks_stranded = (run.updated_at is None) or (run.updated_at.replace(
        tzinfo=timezone.utc) if run.updated_at.tzinfo is None else run.updated_at
    ) < stale_cutoff

    if in_progress and not looks_stranded:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Er loopt al een analyse voor dit project.",
        )

    result = resume_pipeline.delay(run.run_id)
    return ResumeResponse(run_id=run.run_id, task_id=result.id, state="queued")
