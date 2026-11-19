"""
packages/pipeline/stage.py — de bouwsteen van de pipeline.

Een stage is één functionele stap in de analyse (ingest, classificatie,
detectie, fusie, validatie, …). De engine geeft elke stage een
`StageContext` en verantwoordelijkheid voor retry, timeout en checkpointing.

Voorbeeld:

    @stage(id="validate", name="AREI-validatie", requires=("fuse",),
           retry=RetryPolicy(max_attempts=2, base_delay=0))
    def validate_stage(ctx: StageContext) -> None:
        ctx.project = rules_validate(ctx.project)

Belangrijkste vlaggen:

    optional=True  de stage mag zichzelf overslaan (ontbrekende implementatie,
                   feature-flag) én haar mislukking is niet fataal voor de run,
                   tenzij `PipelineOptions.strict` aan staat.
                   → zo draait de pipeline ook als vLLM of torch er niet is.
    replay=True    de stage draait bij hervatten altijd opnieuw, ook als het
                   checkpoint zegt dat hij klaar was (bv. het ophalen van
                   bestandsbytes uit S3 — die zijn niet in het checkpoint
                   opgeslagen).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from packages.schema import Project

from packages.pipeline.errors import PipelineCancelled, StageSkipped
from packages.pipeline.events import EventBus
from packages.pipeline.metrics import MetricsSink, NullMetrics
from packages.pipeline.types import PipelineRun, RetryPolicy, FAST_RETRY

logger = logging.getLogger("imjan.pipeline")


# ---------------------------------------------------------------------------
# Opties
# ---------------------------------------------------------------------------


@dataclass
class PipelineOptions:
    """Zaken die het gedrag van de hele run bepalen."""

    #: optionele stappen mogen niet meer falen zonder de run mee te nemen
    strict: bool = False
    #: checkpoints lezen + wegschrijven (uit = altijd volledig opnieuw)
    checkpointing: bool = True
    #: standaard retry-policy voor stappen die er geen eigen hebben
    default_retry: RetryPolicy = field(default_factory=RetryPolicy)
    #: harde tijdslimiet per stage-poging (seconden); None = geen limiet
    default_timeout_s: float | None = 300.0
    #: extra config voor stappen (fusion-drempels, modelnamen, …)
    extra: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.extra.get(key, default)


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


class SourceLoader(Protocol):
    """Haalt het bronbestand op (S3 in productie, bytes in tests)."""

    def load(self, key: str) -> bytes: ...


class ResultSink:
    """Wordt aangeroepen zodra de run geslaagd is."""

    def publish(self, run: PipelineRun, project: Project) -> None:  # pragma: no cover
        raise NotImplementedError


class NullSink:
    def publish(self, run: PipelineRun, project: Project) -> None:
        return None


@dataclass
class StageContext:
    """Alles wat een stage mag aanraken."""

    project: Project
    #: wordt door de engine gevuld (verse run of hervatting uit checkpoint)
    run: PipelineRun = field(default_factory=PipelineRun)
    options: PipelineOptions = field(default_factory=PipelineOptions)
    #: niet-JSON-waarden tussen stappen (bytes, tussenresultaten)
    payload: dict[str, Any] = field(default_factory=dict)
    events: EventBus = field(default_factory=EventBus)
    metrics: MetricsSink = field(default_factory=NullMetrics)
    loader: SourceLoader | None = None
    sink: ResultSink | None = None
    attempt: int = 1
    stage_id: str | None = None
    _cancel: threading.Event = field(default_factory=threading.Event)

    # -- annulering ----------------------------------------------------------

    def request_cancel(self, reason: str = "geannuleerd door operator") -> None:
        """Veilige annulering: de engine stopt na de huidige stage-poging."""
        self.payload["cancel_reason"] = reason
        self._cancel.set()

    @property
    def cancel_requested(self) -> bool:
        return self._cancel.is_set()

    def check_cancelled(self) -> None:
        if self._cancel.is_set():
            raise PipelineCancelled(
                str(self.payload.get("cancel_reason", "geannuleerd")), stage_id=self.stage_id
            )

    # -- hulp voor stappen ---------------------------------------------------

    def skip(self, reason: str) -> None:
        """Beëindigt de stage als 'overgeslagen' met een reden."""
        raise StageSkipped(reason)

    def load_source(self) -> bytes:
        """Roopt het bronbestand op (idempotent, veilig bij hervatten)."""
        cached = self.payload.get("source_bytes")
        if isinstance(cached, (bytes, bytearray)):
            return bytes(cached)
        key = self.payload.get("s3_key")
        if not key:
            raise StageSkipped("geen s3_key beschikbaar")
        if self.loader is None:
            raise StageSkipped("geen SourceLoader geconfigureerd")
        data = self.loader.load(str(key))
        self.payload["source_bytes"] = data
        return data

    def forget_source(self) -> None:
        """Gooit de ruwe bytes weg (geheugen vrijgeven na normalisatie)."""
        self.payload.pop("source_bytes", None)

    @property
    def log(self) -> logging.Logger:
        return logger


# ---------------------------------------------------------------------------
# Stage
# ---------------------------------------------------------------------------

StageFn = Callable[[StageContext], None]
WhenFn = Callable[[StageContext], bool]


@dataclass
class Stage:
    id: str
    fn: StageFn
    name: str = ""
    description: str = ""
    requires: tuple[str, ...] = ()
    retry: RetryPolicy | None = None
    timeout_s: float | None = None
    optional: bool = False
    replay: bool = False
    when: WhenFn | None = None

    def __call__(self, ctx: StageContext) -> None:
        self.fn(ctx)

    def run(self, ctx: StageContext) -> None:
        self.fn(ctx)

    @property
    def display_name(self) -> str:
        return self.name or self.id

    def effective_retry(self, options: PipelineOptions) -> RetryPolicy:
        return self.retry or options.default_retry

    def effective_timeout(self, options: PipelineOptions) -> float | None:
        if self.timeout_s is not None:
            return self.timeout_s
        return options.default_timeout_s


def stage(
    *,
    id: str,
    name: str = "",
    description: str = "",
    requires: tuple[str, ...] = (),
    retry: RetryPolicy | None = None,
    timeout_s: float | None = None,
    optional: bool = False,
    replay: bool = False,
    when: WhenFn | None = None,
) -> Callable[[StageFn], Stage]:
    """Decorator die een functie omzet in een geregistreerde `Stage`."""

    def decorator(fn: StageFn) -> Stage:
        return Stage(
            id=id,
            fn=fn,
            name=name or id,
            description=description or (fn.__doc__ or "").strip().split("\n")[0],
            requires=tuple(requires),
            retry=retry,
            timeout_s=timeout_s,
            optional=optional,
            replay=replay,
            when=when,
        )

    return decorator
