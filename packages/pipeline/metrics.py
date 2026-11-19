"""
packages/pipeline/metrics.py — metric-sinks.

De engine stuurt twee soorten metriek:

    pipeline.stage.duration{stage=..., outcome=...}  (timing, ms)
    pipeline.stage.attempts{stage=...}               (counter)
    pipeline.run.duration{outcome=...}               (timing, ms)
    pipeline.run.retries                             (counter)
    pipeline.run.resumed                             (counter)

`InMemoryMetrics` is de nulmeting en wordt in tests gebruikt. In productie
hang je hier een StatsD/Prometheus/OTel-sink aan (de interface is bewust
miniem: increment + timing), of je gebruikt `LoggingMetrics` tot er iets
echts staat.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Protocol

logger = logging.getLogger("imjan.pipeline.metrics")


class MetricsSink(Protocol):
    def increment(self, name: str, value: float = 1, tags: dict[str, str] | None = None) -> None: ...

    def timing(self, name: str, value_ms: float, tags: dict[str, str] | None = None) -> None: ...


def _key(name: str, tags: dict[str, str] | None) -> str:
    if not tags:
        return name
    return name + "{" + ",".join(f"{k}={v}" for k, v in sorted(tags.items())) + "}"


class InMemoryMetrics:
    """Telt alles op in geheugen; ideaal voor asserts in tests."""

    def __init__(self) -> None:
        self.counters: dict[str, float] = defaultdict(float)
        self.timings: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, value: float = 1, tags: dict[str, str] | None = None) -> None:
        self.counters[_key(name, tags)] += value

    def timing(self, name: str, value_ms: float, tags: dict[str, str] | None = None) -> None:
        self.timings[_key(name, tags)].append(value_ms)

    def counter(self, name: str, **tags: str) -> float:
        return self.counters.get(_key(name, tags), 0.0)

    def last_timing(self, name: str, **tags: str) -> float | None:
        values = self.timings.get(_key(name, tags))
        return values[-1] if values else None

    @property
    def total_retries(self) -> float:
        return self.counters.get("pipeline.run.retries", 0.0)


class LoggingMetrics:
    """Schrijft metriek naar de log — bruikbaar tot er een echte backend is."""

    def increment(self, name: str, value: float = 1, tags: dict[str, str] | None = None) -> None:
        logger.info("metric %s%s +%s", name, tags or {}, value)

    def timing(self, name: str, value_ms: float, tags: dict[str, str] | None = None) -> None:
        logger.info("metric %s%s %.1fms", name, tags or {}, value_ms)


class NullMetrics:
    """Doet niets — de standaard als niemand metriek wil."""

    def increment(self, name: str, value: float = 1, tags: dict[str, str] | None = None) -> None:
        return None

    def timing(self, name: str, value_ms: float, tags: dict[str, str] | None = None) -> None:
        return None
