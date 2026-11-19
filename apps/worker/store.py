"""
apps/worker/store.py — checkpointopslag in PostgreSQL.

De engine kent alleen het `CheckpointStore`-protocol; dit is de echte
implementatie op de tabellen die de API ook leest. Sync- SQLAlchemy (geen
event loop) omdat een Celery-worker synchroon is.

Consistentiekeuze: één transactionele upsert per stage. De voortgang die de
review-UI ziet, is dus altijd exact de stand van het checkpoint — er is geen
aparte "voortgangstabel" die kan afwijken.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from apps.shared.database import get_sync_engine
from apps.shared.models import PipelineRunRow, row_to_run, run_to_row
from packages.pipeline.types import PipelineRun

logger = logging.getLogger("imjan.worker.store")


class SqlCheckpointStore:
    """Postgres-implementatie van `packages.pipeline.CheckpointStore`."""

    def __init__(self, engine=None) -> None:
        self._engine = engine or get_sync_engine()
        self._factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    # -- schrijven -----------------------------------------------------------

    def save(self, run: PipelineRun) -> None:
        if not run.project_id:
            raise ValueError(f"Run {run.run_id} heeft geen project_id; opslaan onmogelijk.")
        with Session(self._engine) as session:
            row = session.get(PipelineRunRow, run.run_id)
            if row is None:
                row = PipelineRunRow(run_id=run.run_id, project_id=run.project_id)
                run_to_row(run, row)
                session.add(row)
            else:
                run_to_row(run, row)
            session.commit()

    # -- lezen --------------------------------------------------------------

    def load(self, run_id: str) -> PipelineRun | None:
        with Session(self._engine) as session:
            row = session.get(PipelineRunRow, run_id)
            return row_to_run(row) if row else None

    def latest_for_project(self, project_id: str) -> PipelineRun | None:
        with Session(self._engine) as session:
            row = session.execute(
                select(PipelineRunRow)
                .where(PipelineRunRow.project_id == project_id)
                .order_by(PipelineRunRow.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            return row_to_run(row) if row else None

    def list_for_project(self, project_id: str, limit: int = 20) -> list[PipelineRun]:
        with Session(self._engine) as session:
            rows = session.execute(
                select(PipelineRunRow)
                .where(PipelineRunRow.project_id == project_id)
                .order_by(PipelineRunRow.created_at.desc())
                .limit(limit)
            ).scalars().all()
            return [row_to_run(r) for r in rows]

    # -- extra: nodig voor de sweeper ---------------------------------------

    def stale_runs(self, older_than: datetime, limit: int = 50) -> list[PipelineRun]:
        """Niet-terminale runs die al lang niet bijgewerkt zijn."""
        with Session(self._engine) as session:
            rows = session.execute(
                select(PipelineRunRow)
                .where(
                    PipelineRunRow.state.in_(["pending", "running"]),
                    PipelineRunRow.updated_at < older_than,
                )
                .order_by(PipelineRunRow.updated_at.asc())
                .limit(limit)
            ).scalars().all()
            return [row_to_run(r) for r in rows]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
