"""
packages/pipeline/events.py — gebeurtenisbus voor observability.

De engine emit events; alles wat geïnteresseerd is luistert mee:

    bus = EventBus()
    bus.subscribe(LoggingHandler())          # gestructureerde logs
    bus.subscribe(DBProgressHandler(...))    # schrijft voortgang naar PostgreSQL
    bus.subscribe(lambda ev: ws.push(ev))    # websocket naar de review-UI

Handlers mogen de run niet breken: een exception in een handler wordt
gevangen en gelogd, waarna de bus doorgaat met de volgende handler. Anders
zou een stukje monitoring de hele analyse kunnen platleggen.
"""

from __future__ import annotations

import json
import logging
from typing import Callable, Protocol

from packages.pipeline.types import EventType, PipelineEvent, RunState

logger = logging.getLogger("imjan.pipeline")

Handler = Callable[[PipelineEvent], None]


class EventHandler(Protocol):
    def __call__(self, event: PipelineEvent) -> None: ...


class EventBus:
    """Eenvoudige synchrone broadcast-bus (volgorde = inschrijfvolgorde)."""

    def __init__(self, handlers: list[Handler] | None = None) -> None:
        self._handlers: list[Handler] = list(handlers or [])

    def subscribe(self, handler: Handler) -> Handler:
        self._handlers.append(handler)
        return handler

    def unsubscribe(self, handler: Handler) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    def emit(self, event: PipelineEvent) -> None:
        for handler in list(self._handlers):
            try:
                handler(event)
            except Exception:  # noqa: BLE001 — observability mag nooit falen
                logger.exception("Pipeline-event-handler %r gooide een fout", handler)

    # -- gemak ---------------------------------------------------------------

    def fire(
        self,
        type_: EventType,
        run_id: str,
        *,
        project_id: str = "",
        stage_id: str | None = None,
        attempt: int = 0,
        message: str = "",
        duration_ms: int = 0,
        **data,
    ) -> None:
        self.emit(
            PipelineEvent(
                type=type_,
                run_id=run_id,
                project_id=project_id,
                stage_id=stage_id,
                attempt=attempt,
                message=message,
                duration_ms=duration_ms,
                data=data,
            )
        )


class CallbackHandler:
    """Luistert naar één specifiek event-type."""

    def __init__(self, type_: EventType, fn: Callable[[PipelineEvent], None]) -> None:
        self.type = type_
        self.fn = fn

    def __call__(self, event: PipelineEvent) -> None:
        if event.type == self.type:
            self.fn(event)


class CollectingHandler:
    """Vangt alle events op — bedoeld voor tests en de run-detailpagina."""

    def __init__(self) -> None:
        self.events: list[PipelineEvent] = []

    def __call__(self, event: PipelineEvent) -> None:
        self.events.append(event)

    def of(self, *types: EventType) -> list[PipelineEvent]:
        return [e for e in self.events if e.type in types]

    @property
    def stages(self) -> list[str]:
        """Stage-id's in de volgorde waarin ze *afgerond* werden."""
        return [
            e.stage_id or ""
            for e in self.events
            if e.type in {EventType.STAGE_SUCCEEDED, EventType.STAGE_SKIPPED}
        ]


class LoggingHandler:
    """Schrijft één regel per event — JSON als `json_logs` aan staat."""

    def __init__(self, log: logging.Logger | None = None, json_logs: bool = False) -> None:
        self.log = log or logger
        self.json_logs = json_logs

    def __call__(self, event: PipelineEvent) -> None:
        level = logging.INFO
        if event.type in {EventType.STAGE_FAILED, EventType.RUN_FAILED}:
            level = logging.ERROR
        elif event.type in {EventType.STAGE_RETRYING, EventType.RUN_CANCELLED}:
            level = logging.WARNING

        if self.json_logs:
            payload = event.model_dump(mode="json")
            self.log.log(level, json.dumps(payload, ensure_ascii=False, default=str))
            return

        self.log.log(
            level,
            "%s run=%s stage=%s attempt=%d %s%s",
            event.type.value,
            event.run_id,
            event.stage_id or "-",
            event.attempt,
            event.message,
            f" ({event.duration_ms} ms)" if event.duration_ms else "",
        )


class RunStateUpdater:
    """
    Houdt `PipelineRun.state` en de huidige stage bij op basis van events.

    Zo hoeft de engine zelf geen state-machine te verspreiden over
    handlers: alles roept gewoon `bus.fire(...)` en deze helper volgt mee.
    """

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.state = RunState.PENDING
        self.current_stage: str | None = None

    def __call__(self, event: PipelineEvent) -> None:
        if event.run_id != self.run_id:
            return
        if event.type == EventType.RUN_STARTED:
            self.state = RunState.RUNNING
        elif event.type == EventType.RUN_SUCCEEDED:
            self.state = RunState.SUCCEEDED
            self.current_stage = None
        elif event.type == EventType.RUN_FAILED:
            self.state = RunState.FAILED
        elif event.type == EventType.RUN_CANCELLED:
            self.state = RunState.CANCELLED
        elif event.type == EventType.STAGE_STARTED:
            self.current_stage = event.stage_id
