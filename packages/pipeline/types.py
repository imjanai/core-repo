"""
packages/pipeline/types.py — gedeelde datamodellen van de pipeline.

Alles hier is Pydantic, zodat hetzelfde object:
  * in de engine leeft (in memory),
  * in PostgreSQL als JSONB staat (checkpoint + voortgang voor de API),
  * als payload naar de frontend kan zonder mappers.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Staten
# ---------------------------------------------------------------------------


class StageState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    FAILED = "failed"


class RunState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {RunState.SUCCEEDED, RunState.FAILED, RunState.CANCELLED}


# ---------------------------------------------------------------------------
# Retry-policy
# ---------------------------------------------------------------------------


class RetryPolicy(BaseModel):
    """
    Exponentiële backoff met jitter.

        delay(n) = min(base_delay * multiplier^(n-1), max_delay)

    Met `jitter=True` wordt de helft van de vertraging vastgehouden en de
    andere helft willekeurig gemaakt (equal jitter). Dat voorkomt dat tientallen
    workers die tegelijk op een rate limit botsen ná elkaar opnieuw gaan
    proberen — precies het probleem dat je bij een vLLM-endpoint krijgt.
    """

    max_attempts: int = Field(3, ge=1, le=20)
    base_delay: float = Field(1.0, ge=0.0)
    max_delay: float = Field(60.0, ge=0.0)
    multiplier: float = Field(2.0, ge=1.0)
    jitter: bool = True

    def delay_for(self, attempt: int, rand: Any = None) -> float:
        """Vertraging na poging `attempt` (1-indexeerd)."""
        if self.base_delay <= 0:
            return 0.0
        raw = min(
            self.base_delay * (self.multiplier ** max(attempt - 1, 0)),
            self.max_delay,
        )
        if not self.jitter:
            return raw
        rng = rand or __import__("random").random
        return raw / 2 + rng() * (raw / 2)


NO_RETRY = RetryPolicy(max_attempts=1, base_delay=0.0, jitter=False)
FAST_RETRY = RetryPolicy(max_attempts=4, base_delay=0.25, max_delay=10.0)


# ---------------------------------------------------------------------------
# Resultaten
# ---------------------------------------------------------------------------


class StageResult(BaseModel):
    """Voortgang van één stage — dit is wat de frontend te zien krijgt."""

    stage_id: str
    name: str = ""
    state: StageState = StageState.PENDING
    attempts: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int = 0
    error: str | None = None
    error_type: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)

    @property
    def duration_s(self) -> float:
        return self.duration_ms / 1000


class PipelineRun(BaseModel):
    """
    De volledige staat van één uitvoering.

    `project_snapshot` is het Project-model ná de laatst voltooide stage.
    Daardoor kan een run na een worker-crash hervatten waar het stopte in
    plaats van opnieuw te beginnen.
    """

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    pipeline: str = ""
    state: RunState = RunState.PENDING
    stages: list[StageResult] = Field(default_factory=list)
    current_stage: str | None = None
    error: str | None = None
    project_snapshot: dict[str, Any] | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    celery_task_id: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime = Field(default_factory=_utcnow)

    def stage(self, stage_id: str) -> StageResult | None:
        for s in self.stages:
            if s.stage_id == stage_id:
                return s
        return None

    def done_stages(self) -> set[str]:
        return {
            s.stage_id
            for s in self.stages
            if s.state in {StageState.SUCCEEDED, StageState.SKIPPED}
        }

    @property
    def progress(self) -> float:
        if not self.stages:
            return 0.0
        finished = sum(
            1 for s in self.stages if s.state in {StageState.SUCCEEDED, StageState.SKIPPED}
        )
        return round(finished / len(self.stages), 4)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class EventType(str, Enum):
    RUN_STARTED = "run.started"
    RUN_RESUMED = "run.resumed"
    RUN_SUCCEEDED = "run.succeeded"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"
    STAGE_STARTED = "stage.started"
    STAGE_RETRYING = "stage.retrying"
    STAGE_SUCCEEDED = "stage.succeeded"
    STAGE_SKIPPED = "stage.skipped"
    STAGE_FAILED = "stage.failed"


class PipelineEvent(BaseModel):
    type: EventType
    run_id: str
    project_id: str = ""
    stage_id: str | None = None
    attempt: int = 0
    message: str = ""
    duration_ms: int = 0
    data: dict[str, Any] = Field(default_factory=dict)
    ts: datetime = Field(default_factory=_utcnow)
