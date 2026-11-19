"""
apps/api/tasks.py — compatibeleslaag.

Vroeger stond de hele pipeline monolithisch in dit bestand. De taken staan
nu in `apps/worker` (zoals de README voorschrijft); dit moduul bewaart de
oude importpoort zodat de API-router en eventuele externe code blijven
werken:

    from apps.api.tasks import run_pipeline, celery_app

De API gebruikt `apps.api.pipeline_dispatch` om opdrachten te publiceren.
"""

from __future__ import annotations

from apps.worker.celery_app import celery_app
from apps.worker.tasks import reap_stuck_runs, resume_pipeline, run_pipeline

__all__ = ["celery_app", "run_pipeline", "resume_pipeline", "reap_stuck_runs"]
