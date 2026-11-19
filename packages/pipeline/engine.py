"""
packages/pipeline/engine.py — de orchestrator.

Wat deze engine *enterprise* maakt, concreet:

1. **Volgorde uit een DAG.** Stappen declareren hun afhankelijkheden
   (`requires`). Cirkels, duplicaten en onbekende stappen worden al bij het
   bouwen van de pipeline gedetecteerd, niet midden in de nacht in de worker.

2. **Per-stap retry met backoff + jitter.** Elke stap heeft een eigen
   RetryPolicy. Een S3-hapering wordt vier keer geprobeerd met oplopende
   vertraging; een ongeldig bestandsformaat faalt direct (permanent).

3. **Per-stap timeout.** Een vastgelopen OCR- of VLM-aanroep blokkeert nooit
   de hele worker: na `timeout_s` krijgt de stap een retryable fout.

4. **Checkpoint na elke stap.** Het volledige Project wordt na elke geslaagde
   stap weggeschreven. Na een crash of redeploy hervat de run bij de eerste
   stap die nog niet klaar was — idempotent, zonder dubbel rekenwerk.

5. **Graceful degradation.** Stappen die `optional=True` zijn (detectie, OCR,
   VLM) mogen overslaan of falen zonder dat de run sterft. De elektricien
   krijgt dan een analyse mét waarschuwing in plaats van een foutmelding.
   `options.strict=True` zet dat om in fail-fast (bruikbaar in CI).

6. **Annuleren.** Een operator kan een run stoppen; de engine stopt na de
   huidige stap-poging en zet de staat netjes op `cancelled`.

7. **Observability.** Elke overgang is een event (logs, websocket, DB) en een
   metriek (duur, aantal pogingen, retries, hervattingen).
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Sequence

from packages.schema import Project

from packages.pipeline.checkpoints import CheckpointStore
from packages.pipeline.errors import (
    DagError,
    NotImplementedStage,
    PipelineAlreadyRunning,
    PipelineCancelled,
    PipelineError,
    PipelineFailed,
    StageSkipped,
    StageTimeoutError,
    classify_optional_failure,
    is_retryable,
)
from packages.pipeline.events import EventBus
from packages.pipeline.metrics import MetricsSink, NullMetrics
from packages.pipeline.stage import PipelineOptions, Stage, StageContext
from packages.pipeline.types import (
    EventType,
    PipelineRun,
    RunState,
    StageResult,
    StageState,
)

logger = logging.getLogger("imjan.pipeline")

_TERMINAL = {RunState.SUCCEEDED, RunState.FAILED, RunState.CANCELLED}

#: Hoeveel runs van één project we bekijken bij het blokkeren/zoeken op
#: idempotentiesleutel. Ruim genoeg voor de praktijk, klein genoeg voor de index.
_RUN_SCAN_LIMIT = 50


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json_safe(value: Any) -> Any:
    """Houdt alleen JSON-serialiseerbare waarden over (bytes, callables eruit)."""
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        if isinstance(value, dict):
            return {k: _json_safe(v) for k, v in value.items() if isinstance(k, str)}
        return None
    return value


class Pipeline:
    """Een naamgegeven, geordende verzameling stappen met executeerlogica."""

    def __init__(
        self,
        name: str,
        stages: Sequence[Stage],
        description: str = "",
    ) -> None:
        self.name = name
        self.description = description
        self.stages: list[Stage] = list(stages)
        self._ordered: list[Stage] | None = None

    # ------------------------------------------------------------------ DAG --

    def validate(self) -> list[Stage]:
        """Topologisch sorteren en de graaf controleren. Idempotent."""
        if self._ordered is not None:
            return self._ordered

        by_id: dict[str, Stage] = {}
        for st in self.stages:
            if st.id in by_id:
                raise DagError(f"Dubbele stage-id '{st.id}' in pipeline '{self.name}'.")
            by_id[st.id] = st

        for st in self.stages:
            for dep in st.requires:
                if dep not in by_id:
                    raise DagError(
                        f"Stage '{st.id}' vereist onbekende stage '{dep}' in '{self.name}'."
                    )
                if dep == st.id:
                    raise DagError(f"Stage '{st.id}' vereist zichzelf.")

        # Kahn's algoritme: deterministische volgorde (inschrijfvolgorde als tiebreak)
        pending = dict(by_id)
        ordered: list[Stage] = []
        done: set[str] = set()
        while pending:
            ready = [
                st for st in pending.values() if all(d in done for d in st.requires)
            ]
            if not ready:
                cycle = " -> ".join(sorted(pending))
                raise DagError(f"Cirkel in stage-afhankelijkheden van '{self.name}': {cycle}")
            for st in ready:
                ordered.append(st)
                done.add(st.id)
                del pending[st.id]

        self._ordered = ordered
        return ordered

    @property
    def order(self) -> list[str]:
        return [st.id for st in self.validate()]

    def describe(self) -> list[dict[str, Any]]:
        """Machineleesbare beschrijving — voor docs, tests en de API."""
        return [
            {
                "id": st.id,
                "name": st.display_name,
                "description": st.description,
                "requires": list(st.requires),
                "optional": st.optional,
                "replay": st.replay,
                "timeout_s": st.effective_timeout(PipelineOptions()),
                "max_attempts": st.effective_retry(PipelineOptions()).max_attempts,
            }
            for st in self.validate()
        ]

    # ------------------------------------------------------------------ run --

    def run(
        self,
        ctx: StageContext,
        *,
        store: CheckpointStore | None = None,
        resume: str | PipelineRun | None = None,
        idempotency_key: str | None = None,
        task_ref: str | None = None,
    ) -> PipelineRun:
        """
        Voert de pipeline uit (of hervat een bestaande run).

        `task_ref` legt de extern referentie vast (bv. de Celery-taak-id) zodat
        een operator de run in de broker kan terugvinden.

        Geeft de `PipelineRun` terug. Gooit `PipelineFailed`,
        `PipelineCancelled` of `PipelineAlreadyRunning`.
        """
        ordered = self.validate()
        options = ctx.options
        bus = ctx.events
        metrics = ctx.metrics

        resumed = False

        if resume is not None:
            if isinstance(resume, str):
                if store is None:
                    raise PipelineError("Hervatten vereist een CheckpointStore.")
                existing: PipelineRun | None = store.load(resume)
            else:
                existing = resume
            if existing is None:
                raise PipelineError(f"Onbekende run '{resume}' om te hervatten.")
            if existing.state == RunState.SUCCEEDED:
                # Alleen een geslaagde run heeft niets meer te doen. Een
                # mislukte of geannuleerde run mag een operator altijd
                # hervatten — dat is precies het herstelscenario.
                raise PipelineError(
                    f"Run '{existing.run_id}' is al geslaagd; hervatten heeft geen zin."
                )
            ctx.run = existing
            resumed = True
            if existing.project_snapshot:
                ctx.project = Project.model_validate(existing.project_snapshot)
            if existing.payload:
                ctx.payload = {**existing.payload, **ctx.payload}
        else:
            # Idempotentie: nooit twee lopende runs voor hetzelfde project.
            if store is not None and ctx.project.id:
                # We bekijken alle runs van het project, niet alleen de
                # "nieuwste": op een besturingssysteem met grove klok­resolutie
                # (Windows levert ~16 ms per tik) krijgen opeenvolgende runs
                # hetzelfde `created_at` en kiest een sortering op dat veld
                # zomaar de verkeerde run. Eén niet-terminale run is al genoeg
                # om te blokkeren — de sweeper ruimt gestrande runs op, dus
                # het blokkeren is tijdelijk.
                known = store.list_for_project(ctx.project.id, limit=_RUN_SCAN_LIMIT)
                open_runs = [r for r in known if r.state not in _TERMINAL]
                if open_runs:
                    blocking = max(open_runs, key=lambda r: (r.created_at, r.run_id))
                    raise PipelineAlreadyRunning(
                        f"Project {ctx.project.id} heeft al een run in "
                        f"toestand '{blocking.state.value}'.",
                        run=blocking,
                    )
                if idempotency_key:
                    # Dezelfde sleutel, al succesvol → geen tweede uitvoering.
                    match = next(
                        (
                            r
                            for r in known
                            if r.idempotency_key == idempotency_key
                            and r.state == RunState.SUCCEEDED
                        ),
                        None,
                    )
                    if match is not None:
                        return match

            ctx.run = PipelineRun(
                project_id=ctx.project.id,
                pipeline=self.name,
                state=RunState.RUNNING,
                idempotency_key=idempotency_key,
            )
            # Bekende stages meteen als PENDING registeren → de frontend ziet
            # de volledige checklist vanaf de eerste seconde.
            for st in ordered:
                ctx.run.stages.append(
                    StageResult(stage_id=st.id, name=st.display_name)
                )

        run = ctx.run
        if task_ref:
            run.celery_task_id = task_ref
        run.state = RunState.RUNNING
        run.error = None
        run.current_stage = None
        run.started_at = run.started_at or _now()
        run.updated_at = _now()

        bus.fire(
            EventType.RUN_RESUMED if resumed else EventType.RUN_STARTED,
            run.run_id,
            project_id=run.project_id,
            data={"pipeline": self.name, "stages": len(ordered)},
        )
        if resumed:
            metrics.increment("pipeline.run.resumed")

        run_start = time.perf_counter()
        try:
            for st in ordered:
                ctx.check_cancelled()
                self._run_stage(st, ctx, store)
        except PipelineCancelled as exc:
            run.state = RunState.CANCELLED
            run.error = str(exc)
            run.finished_at = _now()
            self._checkpoint(run, store, ctx)
            bus.fire(
                EventType.RUN_CANCELLED,
                run.run_id,
                project_id=run.project_id,
                stage_id=run.current_stage,
                message=str(exc),
            )
            metrics.timing(
                "pipeline.run.duration",
                (time.perf_counter() - run_start) * 1000,
                {"outcome": "cancelled"},
            )
            raise
        except PipelineFailed as exc:
            run.state = RunState.FAILED
            run.error = str(exc)
            run.current_stage = exc.stage_id
            run.finished_at = _now()
            self._checkpoint(run, store, ctx)
            bus.fire(
                EventType.RUN_FAILED,
                run.run_id,
                project_id=run.project_id,
                stage_id=exc.stage_id,
                message=str(exc),
                attempts=exc.attempts,
            )
            metrics.timing(
                "pipeline.run.duration",
                (time.perf_counter() - run_start) * 1000,
                {"outcome": "failed"},
            )
            raise

        # --- succes ---------------------------------------------------------
        run.state = RunState.SUCCEEDED
        run.current_stage = None
        run.error = None
        run.finished_at = _now()
        run.updated_at = _now()
        run.project_snapshot = ctx.project.model_dump(mode="json")
        run.payload = _json_safe(ctx.payload) or {}
        self._checkpoint(run, store, ctx)

        if ctx.sink is not None:
            try:
                ctx.sink.publish(run, ctx.project)
            except Exception as exc:  # noqa: BLE001 — publicatie mag de run niet slopen
                logger.exception("Resultaat kon niet gepubliceerd worden")
                run.payload["publish_error"] = str(exc)

        bus.fire(
            EventType.RUN_SUCCEEDED,
            run.run_id,
            project_id=run.project_id,
            message=f"{sum(1 for s in run.stages if s.state == StageState.SUCCEEDED)} stappen voltooid",
        )
        metrics.timing(
            "pipeline.run.duration",
            (time.perf_counter() - run_start) * 1000,
            {"outcome": "succeeded"},
        )
        return run

    # ---------------------------------------------------------------- stage --

    def _run_stage(self, st: Stage, ctx: StageContext, store: CheckpointStore | None) -> None:
        run = ctx.run
        options = ctx.options
        bus = ctx.events
        metrics = ctx.metrics
        result = run.stage(st.id) or StageResult(stage_id=st.id, name=st.display_name)
        if run.stage(st.id) is None:
            run.stages.append(result)
        result.name = st.display_name

        # 1. Bestaat de implementatie (nog) niet / staat ze uit?
        if st.when is not None:
            try:
                enabled = st.when(ctx)
            except Exception:  # noqa: BLE001
                logger.exception("when()-conditie van stage %s faalde", st.id)
                enabled = False
            if not enabled:
                self._finish_stage(
                    result, ctx, store, StageState.SKIPPED,
                    message="voorwaarde niet voldaan (feature uit of niet van toepassing)",
                )
                return

        # 2. Hervatten: reeds voltooide stappen overslaan (behalve replay-stappen)
        done_before = run.done_stages()
        if st.id in done_before and not st.replay:
            bus.fire(
                EventType.STAGE_SKIPPED,
                run.run_id,
                project_id=run.project_id,
                stage_id=st.id,
                message="hervat uit checkpoint",
                from_checkpoint=True,
            )
            return

        policy = st.effective_retry(options)
        timeout = st.effective_timeout(options)
        run.current_stage = st.id

        result.state = StageState.RUNNING
        result.started_at = result.started_at or _now()
        result.attempts = 0
        result.error = None
        result.error_type = None
        run.updated_at = _now()
        self._checkpoint(run, store, ctx)

        attempt = 0
        while True:
            attempt += 1
            result.attempts = attempt
            ctx.attempt = attempt
            ctx.stage_id = st.id
            started = time.perf_counter()
            ctx.metrics.increment("pipeline.stage.attempts", tags={"stage": st.id})

            bus.fire(
                EventType.STAGE_STARTED,
                run.run_id,
                project_id=run.project_id,
                stage_id=st.id,
                attempt=attempt,
            )

            try:
                ctx.check_cancelled()
                self._execute(st, ctx, timeout)
            except StageSkipped as skipped:
                if options.strict and isinstance(skipped, NotImplementedStage):
                    # CI wil horen dat de parser ontbreekt; productie gaat
                    # er gewoon mee door (zie PipelineOptions.strict).
                    message = f"verplichte stap mist implementatie: {skipped.reason}"
                    self._finish_stage(
                        result, ctx, store, StageState.FAILED,
                        message=message, error_type="NotImplementedStage",
                    )
                    raise PipelineFailed(
                        f"Stage '{st.id}': {message}",
                        stage_id=st.id,
                        attempts=result.attempts,
                        cause=skipped,
                    ) from skipped
                self._finish_stage(
                    result, ctx, store, StageState.SKIPPED, message=skipped.reason
                )
                return
            except PipelineCancelled:
                raise
            except BaseException as exc:  # noqa: BLE001 — alles classificeren
                duration_ms = int((time.perf_counter() - started) * 1000)
                result.duration_ms += duration_ms
                retryable = is_retryable(exc)

                # Optionele stap zonder implementatie (torch, vLLM, een parser
                # die nog niet bestaat) → netjes overslaan, niet opnieuw proberen.
                if st.optional and classify_optional_failure(exc):
                    self._finish_stage(
                        result, ctx, store, StageState.SKIPPED,
                        message=f"niet beschikbaar: {exc}",
                    )
                    return

                if retryable and attempt < policy.max_attempts:
                    delay = policy.delay_for(attempt)
                    metrics.increment("pipeline.run.retries")
                    bus.fire(
                        EventType.STAGE_RETRYING,
                        run.run_id,
                        project_id=run.project_id,
                        stage_id=st.id,
                        attempt=attempt,
                        message=f"{type(exc).__name__}: {exc} — opnieuw over {delay:.1f}s",
                        next_delay_s=round(delay, 3),
                    )
                    logger.warning(
                        "Stage %s faalde (poging %d/%d): %s",
                        st.id, attempt, policy.max_attempts, exc,
                    )
                    result.state = StageState.RETRYING
                    run.updated_at = _now()
                    if delay > 0:
                        self._sleep(delay, ctx)
                    continue

                # Definitief gefaald.
                message = f"{type(exc).__name__}: {exc}"
                if st.optional and not options.strict:
                    logger.warning(
                        "Optionele stage %s gefaald → run gaat door (degraded): %s",
                        st.id, message,
                    )
                    self._finish_stage(
                        result, ctx, store, StageState.FAILED,
                        message=message, error_type=type(exc).__name__,
                    )
                    return

                self._finish_stage(
                    result, ctx, store, StageState.FAILED,
                    message=message, error_type=type(exc).__name__,
                )
                raise PipelineFailed(
                    f"Stage '{st.id}' mislukt: {message}",
                    stage_id=st.id,
                    attempts=attempt,
                    cause=exc,
                ) from exc
            else:
                duration_ms = int((time.perf_counter() - started) * 1000)
                result.duration_ms += duration_ms
                result.detail.setdefault("runs", 0)
                result.detail["runs"] += 1
                metrics.timing(
                    "pipeline.stage.duration",
                    duration_ms,
                    tags={"stage": st.id, "outcome": "succeeded"},
                )
                self._finish_stage(
                    result, ctx, store, StageState.SUCCEEDED, duration_ms=duration_ms
                )
                return

    # ------------------------------------------------------------- helpers --

    def _execute(self, st: Stage, ctx: StageContext, timeout: float | None) -> None:
        """Voert één poging uit, met optionele tijdslimiet in een daemon-thread."""
        if timeout is None or timeout <= 0:
            st.run(ctx)
            return

        box: dict[str, Any] = {}

        def target() -> None:
            try:
                st.run(ctx)
            except BaseException as exc:  # noqa: BLE001
                box["exc"] = exc
                box["tb"] = exc.__traceback__

        worker = threading.Thread(
            target=target, name=f"pipeline-{ctx.run.run_id[:8]}-{st.id}", daemon=True
        )
        worker.start()
        worker.join(timeout)

        if worker.is_alive():
            metrics_tags = {"stage": st.id}
            ctx.metrics.increment("pipeline.stage.timeouts", tags=metrics_tags)
            raise StageTimeoutError(
                f"Stage '{st.id}' overschrijdt de tijdslimiet van {timeout:.0f}s",
                stage_id=st.id,
            )
        if "exc" in box:
            raise box["exc"].with_traceback(box["tb"])

    @staticmethod
    def _sleep(delay: float, ctx: StageContext) -> None:
        """Slaapt in kleine stukjes zodat annuleren snel reageert."""
        deadline = time.monotonic() + delay
        while time.monotonic() < deadline:
            if ctx.cancel_requested:
                return
            time.sleep(min(0.1, max(deadline - time.monotonic(), 0.01)))

    def _finish_stage(
        self,
        result: StageResult,
        ctx: StageContext,
        store: CheckpointStore | None,
        state: StageState,
        *,
        message: str = "",
        error_type: str | None = None,
        duration_ms: int = 0,
    ) -> None:
        run = ctx.run
        result.state = state
        result.finished_at = _now()
        result.error = message if state in {StageState.FAILED, StageState.SKIPPED} else None
        result.error_type = error_type
        if duration_ms:
            result.duration_ms = max(result.duration_ms, duration_ms)
        run.updated_at = _now()

        event_type = {
            StageState.SUCCEEDED: EventType.STAGE_SUCCEEDED,
            StageState.SKIPPED: EventType.STAGE_SKIPPED,
            StageState.FAILED: EventType.STAGE_FAILED,
        }[state]

        ctx.events.fire(
            event_type,
            run.run_id,
            project_id=run.project_id,
            stage_id=result.stage_id,
            attempt=result.attempts,
            message=message,
            duration_ms=result.duration_ms,
        )
        ctx.metrics.increment(
            "pipeline.stage.outcome",
            tags={"stage": result.stage_id, "outcome": state.value},
        )

        # Checkpoint: alleen niet-terminal stappen overschrijven is onveilig,
        # dus we schrijven altijd het volledige run-object weg.
        self._checkpoint(run, store, ctx)

    @staticmethod
    def _checkpoint(run: PipelineRun, store: CheckpointStore | None, ctx: StageContext) -> None:
        if store is None or not ctx.options.checkpointing:
            return
        # Project-stand bijwerken vóór het wegschrijven.
        try:
            run.project_snapshot = ctx.project.model_dump(mode="json")
            run.payload = _json_safe(ctx.payload) or {}
        except Exception:  # noqa: BLE001
            logger.exception("Project-snapshot kon niet gemaakt worden")
        try:
            store.save(run)
        except Exception as exc:  # noqa: BLE001 — een dichte DB mag de analyse niet stoppen
            logger.exception("Checkpoint opslaan mislukt voor run %s", run.run_id)
            ctx.metrics.increment("pipeline.checkpoint.errors")


# ---------------------------------------------------------------------------
# Hulp om snel een eenmalige run te starten
# ---------------------------------------------------------------------------


def run_once(
    pipeline: Pipeline,
    project: Project,
    *,
    payload: dict[str, Any] | None = None,
    options: PipelineOptions | None = None,
    store: CheckpointStore | None = None,
    events: EventBus | None = None,
    metrics: MetricsSink | None = None,
    ctx: StageContext | None = None,
) -> PipelineRun:
    """Bouwt een context en draait de pipeline één keer — handig in tests/CLI."""
    context = ctx or StageContext(
        project=project,
        options=options or PipelineOptions(),
        payload=payload or {},
        events=events or EventBus(),
        metrics=metrics or NullMetrics(),
    )
    return pipeline.run(context, store=store)
