"""
packages/pipeline/checkpoints.py — waar de run-state bewaard wordt.

Een checkpoint wordt na *elke* afgeronde stage weggeschreven. Daardoor kan:

  * een worker die middenin een stage crasht → hervatten bij de volgende stage;
  * de API → live voortgang tonen zonder de engine te bevragen;
  * een operator → een mislukte run opnieuw draaien zonder het rekenwerk
    van de succesvolle stappen te herhalen (idempotent hervatten).

Implementaties:

  * InMemoryCheckpointStore   — tests / eenmalige CLI-runs
  * FileCheckpointStore       — lokaal debuggen zonder database
  * CheckpointStore (Protocol) — de contractnaam; PostgreSQL-versie woont in
                                 apps/worker/store.py omdat die SQLAlchemy
                                 en de tabellen van de API nodig heeft.

Gegarandeerd gedrag van elke implementatie:
  * `save` is idempotent (zelfde run_id → zelfde staat, geen duplicaten);
  * `load` op een onbekend run_id geeft None, geen exception;
  * `save` schrijft het volledige object, nooit een delta.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Protocol

from packages.pipeline.types import PipelineRun


class CheckpointStore(Protocol):
    def save(self, run: PipelineRun) -> None: ...

    def load(self, run_id: str) -> PipelineRun | None: ...

    def latest_for_project(self, project_id: str) -> PipelineRun | None: ...

    def list_for_project(self, project_id: str, limit: int = 20) -> list[PipelineRun]: ...


class InMemoryCheckpointStore:
    """Thread-safe dict-store. Snel, vluchtig, standaard in tests."""

    def __init__(self) -> None:
        self._runs: dict[str, PipelineRun] = {}
        self._lock = threading.RLock()
        self.save_count = 0

    def save(self, run: PipelineRun) -> None:
        with self._lock:
            self._runs[run.run_id] = run.model_copy(deep=True)
            self.save_count += 1

    def load(self, run_id: str) -> PipelineRun | None:
        with self._lock:
            run = self._runs.get(run_id)
            return run.model_copy(deep=True) if run else None

    def latest_for_project(self, project_id: str) -> PipelineRun | None:
        runs = self.list_for_project(project_id, limit=1)
        return runs[0] if runs else None

    def list_for_project(self, project_id: str, limit: int = 20) -> list[PipelineRun]:
        with self._lock:
            matching = [r for r in self._runs.values() if r.project_id == project_id]
        matching.sort(key=lambda r: r.created_at, reverse=True)
        return matching[:limit]


class FileCheckpointStore:
    """Één JSON-bestand per run in een map — handig voor lokaal debuggen."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        safe = "".join(c for c in run_id if c.isalnum() or c in "-_") or "run"
        return self.directory / f"{safe}.json"

    def save(self, run: PipelineRun) -> None:
        path = self._path(run.run_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        tmp.replace(path)  # atomisch — nooit een half checkpoint

    def load(self, run_id: str) -> PipelineRun | None:
        path = self._path(run_id)
        if not path.exists():
            return None
        return PipelineRun.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def latest_for_project(self, project_id: str) -> PipelineRun | None:
        runs = self.list_for_project(project_id, limit=1)
        return runs[0] if runs else None

    def list_for_project(self, project_id: str, limit: int = 20) -> list[PipelineRun]:
        runs: list[PipelineRun] = []
        for path in self.directory.glob("*.json"):
            try:
                run = PipelineRun.model_validate(json.loads(path.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001 — corrupt checkpoint negeren
                continue
            if run.project_id == project_id:
                runs.append(run)
        runs.sort(key=lambda r: r.created_at, reverse=True)
        return runs[:limit]
