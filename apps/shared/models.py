"""
apps/shared/models.py — SQLAlchemy ORM-tabellen.

Kolommen die variabele JSON-structuren bevatten (rooms, symbols, materials,
warnings) worden opgeslagen als JSONB. Zo is er één bron van waarheid
(het Pydantic-model in packages/schema) en hoeven we geen genormaliseerde
subtabellen bij te houden voor de eerste versie.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.shared.database import Base
from packages.schema import ProjectStatus, FileType
from packages.pipeline.types import PipelineRun, RunState, StageResult


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(
        SAEnum(ProjectStatus, values_callable=lambda e: [m.value for m in e]),
        default=ProjectStatus.UPLOADED.value,
    )
    file_type: Mapped[str] = mapped_column(
        SAEnum(FileType, values_callable=lambda e: [m.value for m in e]),
        default=FileType.UNKNOWN.value,
    )
    original_filename: Mapped[str] = mapped_column(String(512), default="")
    s3_key: Mapped[str] = mapped_column(String(1024), default="")
    scale: Mapped[float] = mapped_column(Float, default=1.0)

    # Genormaliseerde velden als JSONB
    rooms: Mapped[list] = mapped_column(JSONB, default=list)
    symbols: Mapped[list] = mapped_column(JSONB, default=list)
    materials: Mapped[list] = mapped_column(JSONB, default=list)
    warnings: Mapped[list] = mapped_column(JSONB, default=list)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Celery task-id zodat de status gepolled kan worden
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class PipelineRunRow(Base):
    """
    Eén regel per pipeline-uitvoering (checkpoint + voortgang).

    Dit is de bron van waarheid voor:
      * live voortgang in de review-UI (stadium per stadium),
      * hervatten na een crash of redeploy,
      * de auditvraag "welke analyse heeft dit resultaat opgeleverd?".
    """

    __tablename__ = "pipeline_runs"

    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)
    pipeline: Mapped[str] = mapped_column(String(64), default="analyse")
    state: Mapped[str] = mapped_column(String(16), default=RunState.PENDING.value)
    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: lijst van StageResult-dumps: volgorde, pogingen, duur en fouten
    stages: Mapped[list] = mapped_column(JSONB, default=list)
    #: Project-model na de laatst voltooide stap — de basis voor hervatten
    project_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


# ---------------------------------------------------------------------------
# Mappers tussen het pipeline-pakket en de tabellen
# ---------------------------------------------------------------------------


def run_to_row(run: PipelineRun, row: PipelineRunRow) -> PipelineRunRow:
    """Schrijft een PipelineRun in een bestaande rij (idempotent)."""
    row.run_id = run.run_id
    row.project_id = run.project_id or row.project_id
    row.pipeline = run.pipeline
    row.state = run.state.value
    row.current_stage = run.current_stage
    row.error = run.error
    row.stages = [s.model_dump(mode="json") for s in run.stages]
    row.project_snapshot = run.project_snapshot or {}
    row.payload = run.payload or {}
    row.idempotency_key = run.idempotency_key
    row.celery_task_id = run.celery_task_id
    row.started_at = run.started_at
    row.finished_at = run.finished_at
    row.updated_at = _now()
    return row


def row_to_run(row: PipelineRunRow) -> PipelineRun:
    """Bouwt het PipelineRun-model terug uit de database."""
    return PipelineRun(
        run_id=row.run_id,
        project_id=row.project_id,
        pipeline=row.pipeline,
        state=RunState(row.state),
        current_stage=row.current_stage,
        error=row.error,
        stages=[StageResult.model_validate(s) for s in (row.stages or [])],
        project_snapshot=row.project_snapshot or None,
        payload=row.payload or {},
        idempotency_key=row.idempotency_key,
        celery_task_id=row.celery_task_id,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
        updated_at=row.updated_at,
    )


class CorrectionRow(Base):
    __tablename__ = "corrections"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(32))
    symbol_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    new_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
