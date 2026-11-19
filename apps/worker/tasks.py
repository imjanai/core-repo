"""
apps/worker/tasks.py — de Celery-taken rond de analysepipeline.

Drie taken:

    elektro_ai.run_pipeline       nieuwe analyse (roepen vanuit de API)
    elektro_ai.resume_pipeline    hervatten na crash/storing of op verzoek
    elektro_ai.reap_stuck_runs    periodieke sweeper (beat)

De verdeelde verantwoordelijkheid:

  * `packages/pipeline` bepaalt *wat* er gebeurt en herhaalt stappen die
    tijdelijk falen (backoff, timeout, checkpoint, resume);
  * deze module bepaalt *waar* het draait (broker, database, S3) en vertaalt
    de uitkomst naar projectstatussen;
  * Celery itself behandelt alleen infrastructuurfouten (broker weg, DB niet
    bereikbaar) met een korte retry — een defecte parser wordt niet drie
    keer door Celery opnieuw gestuurd, dat doet de engine al.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from celery import states
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.shared.config import settings
from apps.shared.database import get_sync_engine as get_engine
from apps.shared.models import PipelineRunRow, ProjectRow, row_to_run
from apps.shared.queue import REAP_STUCK_RUNS, RESUME_PIPELINE, RUN_PIPELINE, celery_app
from apps.worker.loader import ProjectResultSink, S3SourceLoader
from apps.worker.store import SqlCheckpointStore, resume_claim_active
from packages.pipeline import (
    EventBus,
    LoggingHandler,
    NullMetrics,
    PipelineAlreadyRunning,
    PipelineCancelled,
    PipelineFailed,
    PipelineOptions,
    RunState,
    StageContext,
    build_default_pipeline,
)
from packages.schema import FileType, Project, ProjectStatus

logger = logging.getLogger("imjan.worker")

_RETRYABLE_STAGES = 3  # standaardpogingen per stage; override via PipelineOptions


# ---------------------------------------------------------------------------
# Infrastructuur-hulpjes
# ---------------------------------------------------------------------------


def _store(engine) -> SqlCheckpointStore:
    return SqlCheckpointStore(engine)


def _set_project_status(
    engine,
    project_id: str,
    status: ProjectStatus,
    *,
    task_id: str | None = None,
    error: str | None = None,
) -> None:
    """Zet de projectstatus; een dichte database mag de taak niet laten crashen."""
    try:
        with Session(engine) as session:
            row = session.get(ProjectRow, project_id)
            if row is None:
                logger.warning("Project %s bestaat niet meer (status %s geskipt)",
                               project_id, status.value)
                return
            row.status = status.value
            if task_id:
                row.task_id = task_id
            if error is not None:
                row.meta = {**(row.meta or {}), "pipeline_error": error}
            session.commit()
    except Exception:  # noqa: BLE001
        logger.exception("Status van project %s kon niet bijgewerkt worden", project_id)


def _load_project(engine, project_id: str, fallback_name: str = "") -> Project:
    with Session(engine) as session:
        row = session.get(ProjectRow, project_id)
        if row is None:
            return Project(id=project_id, name=fallback_name)
        return Project(
            id=row.id,
            name=row.name,
            status=ProjectStatus(row.status),
            file_type=FileType(row.file_type),
            scale=row.scale,
            rooms=row.rooms or [],
            symbols=row.symbols or [],
            materials=row.materials or [],
            warnings=row.warnings or [],
            meta=row.meta or {},
        )


def build_context(
    project: Project,
    *,
    payload: dict | None = None,
    engine=None,
    options: PipelineOptions | None = None,
) -> StageContext:
    """Stelt de context samen die elke stage nodig heeft."""
    engine = engine or get_engine()
    events = EventBus([LoggingHandler(logger)])
    return StageContext(
        project=project,
        payload=payload or {},
        options=options
        or PipelineOptions(
            default_timeout_s=float(settings.pipeline_soft_time_limit),
            extra={"vlm_enabled": True},
        ),
        events=events,
        metrics=NullMetrics(),
        loader=S3SourceLoader(),
        sink=ProjectResultSink(engine, project.id),
    )


# ---------------------------------------------------------------------------
# Taak: nieuwe analyse
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name=RUN_PIPELINE,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
)
def run_pipeline(self, project_id: str, s3_key: str, file_type: str = "unknown"):
    """
    Voert de volledige analysepipeline uit voor één geüpload bestand.

    Terugwaarde is een klein JSON-dict (bruikbaar voor tests en de API).
    Gooit alleen een Celery-retry bij *infrastructuur*fouten; een inhoudelijke
    mislukking wordt als mislukt resultaat teruggegeven.
    """
    engine = None
    try:
        engine = get_engine()
        store = _store(engine)

        project = _load_project(engine, project_id)
        ctx = build_context(
            project,
            payload={
                "s3_key": s3_key,
                "filename": project.name,
                "file_type_hint": file_type,
            },
            engine=engine,
        )

        _set_project_status(engine, project_id, ProjectStatus.PROCESSING,
                            task_id=self.request.id)

        pipeline = build_default_pipeline()
        run = pipeline.run(
            ctx,
            store=store,
            # Eén actieve analyse per project: dubbele broker-leveringen en
            # dubbeldrukken op 'uploaderen' leveren geen tweede run op.
            idempotency_key=project_id,
            task_ref=self.request.id,
        )

    except PipelineAlreadyRunning as exc:
        existing = exc.run
        logger.info("Project %s al in behandeling (run %s) — niets gedaan.",
                    project_id, getattr(existing, "run_id", "?"))
        return {"state": "skipped", "reason": "already_running",
                "run_id": getattr(existing, "run_id", None)}

    except PipelineFailed as exc:
        logger.error("Analyse gefaald voor project %s in stage %s: %s",
                     project_id, exc.stage_id, exc)
        _set_project_status(engine, project_id, ProjectStatus.FAILED, error=str(exc))
        return {"state": "failed", "stage": exc.stage_id,
                "attempts": exc.attempts, "error": str(exc)}

    except PipelineCancelled as exc:
        logger.warning("Analyse geannuleerd voor project %s: %s", project_id, exc)
        _set_project_status(engine, project_id, ProjectStatus.FAILED,
                            error=f"geannuleerd: {exc}")
        return {"state": "cancelled", "error": str(exc)}

    except Exception as exc:  # noqa: BLE001 — infrastructuur
        if engine is None or self.request.retries >= (self.max_retries or 0):
            logger.exception("Analyse definitief mislukt voor project %s", project_id)
            if engine is not None:
                _set_project_status(engine, project_id, ProjectStatus.FAILED,
                                    error=f"infrastructuur: {exc}")
            raise
        logger.warning("Infrastructuurfout voor project %s, retry over 60s: %s",
                       project_id, exc)
        raise self.retry(exc=exc)

    # --- succes ------------------------------------------------------------
    if run.payload.get("publish_error"):
        # Het rekenwerk is klaar maar het wegschrijven is mislukt: dat is een
        # infrastructuurfout en mag gerust opnieuw.
        raise self.retry(exc=RuntimeError(f"publiceren mislukt: "
                                          f"{run.payload['publish_error']}"))

    return {
        "state": "succeeded",
        "run_id": run.run_id,
        "project_id": project_id,
        "progress": run.progress,
        "symbols": len(ctx.project.symbols),
        "materials": len(ctx.project.materials),
        "warnings": len(ctx.project.warnings),
        "stages": {s.stage_id: s.state.value for s in run.stages},
    }


# ---------------------------------------------------------------------------
# Taak: hervatten
# ---------------------------------------------------------------------------


def _resume_lease() -> timedelta:
    return timedelta(seconds=max(
        settings.pipeline_hard_time_limit + 60, settings.stale_after_minutes * 60,
    ))


@celery_app.task(
    bind=True,
    name=RESUME_PIPELINE,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
)
def resume_pipeline(self, run_id: str):
    """Hervat een analyse bij de eerste stap die nog niet klaar was."""
    engine = get_engine()
    store = _store(engine)

    token = str(uuid4())
    lease = _resume_lease()
    run = store.claim_resume(run_id, token, lease)
    if run is None:
        latest = store.load(run_id)
        if latest is None:
            return {"state": "missing", "run_id": run_id}
        if latest.state == RunState.SUCCEEDED:
            return {"state": "succeeded", "run_id": run_id}
        return {"state": "claimed_elsewhere", "run_id": run_id}

    try:
        project = _load_project(engine, run.project_id)
        ctx = build_context(project, payload=dict(run.payload), engine=engine)
        _set_project_status(engine, run.project_id, ProjectStatus.PROCESSING,
                            task_id=self.request.id)
        pipeline = build_default_pipeline()
        resumed = pipeline.run(ctx, store=store, resume=run, task_ref=self.request.id)
    except PipelineFailed as exc:
        _set_project_status(engine, run.project_id, ProjectStatus.FAILED, error=str(exc))
        return {"state": "failed", "run_id": run_id, "stage": exc.stage_id,
                "error": str(exc)}
    except PipelineCancelled as exc:
        _set_project_status(engine, run.project_id, ProjectStatus.FAILED,
                            error=f"geannuleerd: {exc}")
        return {"state": "cancelled", "run_id": run_id}
    except Exception as exc:  # noqa: BLE001
        if self.request.retries >= (self.max_retries or 0):
            logger.exception("Hervatten van run %s definitief mislukt", run_id)
            _set_project_status(engine, run.project_id, ProjectStatus.FAILED,
                                error=f"infrastructuur: {exc}")
            raise
        raise self.retry(exc=exc)

    finally:
        try:
            store.release_resume(run_id, token)
        except Exception:  # noqa: BLE001
            logger.exception("Hervatreservering voor run %s kon niet worden vrijgegeven", run_id)

    return {"state": "succeeded", "run_id": run_id, "progress": resumed.progress}


# ---------------------------------------------------------------------------
# Taak: sweeper
# ---------------------------------------------------------------------------


@celery_app.task(name=REAP_STUCK_RUNS)
def reap_stuck_runs():
    """
    Ruimt runs op die geen levende worker meer hebben.

    Een run kan stranden doordat de broker leegliep, een worker wegviel met
    een niet-afgehandelde taak, of iemand de container handmatig stopte.
    De sweeper kijkt elke `stale_check_seconds` of er runs zijn die ouder zijn
    dan `stale_after_minutes` en waarvan de Celery-taak niet meer loopt.

    Herstelbeleid: opnieuw proberen tot `max_run_resumes` keer, daarna
    definitief markeeren als gefaald — oneindig herstarten is erger dan
    een foutmelding.
    """
    engine = get_engine()
    store = _store(engine)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.stale_after_minutes)

    with Session(engine) as session:
        rows = session.execute(
            select(PipelineRunRow)
            .where(
                PipelineRunRow.state.in_(["pending", "running"]),
                PipelineRunRow.updated_at < cutoff,
            )
            .order_by(PipelineRunRow.updated_at.asc())
            .limit(50)
        ).scalars().all()
        stale = [row_to_run(r) for r in rows]

    lease = _resume_lease()
    reclaimed = 0
    given_up = 0

    for run in stale:
        # Leeft de oorspronkelijke taak nog? Dan is dit geen strand.
        if run.celery_task_id:
            try:
                task_state = celery_app.AsyncResult(run.celery_task_id).state
            except Exception:  # noqa: BLE001
                task_state = states.PENDING
            if task_state in (states.STARTED, states.SUCCESS):
                continue

        resumes = int(run.payload.get("resume_count", 0))
        with Session(engine) as session:
            row = session.get(PipelineRunRow, run.run_id, with_for_update=True)
            if row is None:
                continue
            current = row_to_run(row)
            now = datetime.now(timezone.utc)
            if current.updated_at != run.updated_at or resume_claim_active(current, lease, now):
                continue
            if resumes >= settings.max_run_resumes:
                row.state = RunState.FAILED.value
                row.error = (
                    f"Na {resumes} hervatpogingen nog steeds niet voltooid; "
                    "handmatige inspectie vereist."
                )
                row.finished_at = now
            else:
                row.payload = {**(row.payload or {}), "resume_count": resumes + 1}
                resume_pipeline.delay(run.run_id)
            row.updated_at = now
            error = row.error
            session.commit()

        if resumes >= settings.max_run_resumes:
            _set_project_status(engine, run.project_id, ProjectStatus.FAILED, error=error)
            given_up += 1
            logger.error("Run %s definitief opgegeven na %d hervattingen", run.run_id, resumes)
        else:
            reclaimed += 1
            logger.warning("Gestrande run %s opnieuw in de wachtrij gezet (poging %d)",
                           run.run_id, resumes + 1)

    if stale:
        logger.info("Sweeper: %d gestrande run(s), %d hervat, %d opgegeven",
                    len(stale), reclaimed, given_up)
    return {"checked": len(stale), "reclaimed": reclaimed, "given_up": given_up}
