"""
apps/worker/celery_app.py — de Celery-configuratie van de analyseworker.

Start een worker met:

    uv run celery -A apps.worker.celery_app worker --loglevel=info --concurrency=2

Alles wat hieronder staat is bewust gekozen voor *betrouwbaar* werken op
achtergrondwerk dat minuten kan duren:

* `acks_late=True` + `reject_on_worker_lost=True`
      De boodschap wordt pas bevestigd als de taak klaar is. Sterft de
      worker (OOM door torch, redeploy, laptop dicht), dan gaat de taak
      terug in de wachtrij in plaats van verloren.
* `worker_prefetch_multiplier=1`
      Een worker haalt precies één taak tegelijk. Met prefetch 4 zou één
      kapotte GPU-taak drie andere projecten vasthouden.
* `visibility_timeout`
      Na dit aantal seconden mag Redis een "vergeten" boodschap opnieuw
      uitdelen. Moet groter zijn dan de langste pipeline-run.
* `task_time_limit`
      Harde stop na de tijdslimiet: ook een doodlopende stage breekt los.
* `worker_max_tasks_per_child`
      Periodiek herstarten van het proces houdt GPU-/fragmentatiegeheugen schoon.
* `beat_schedule`
      Een sweeper ruimt runs op die op de een of andere manier geen
      worker meer hebben gevonden (bijv. leeglopende broker).
"""

from __future__ import annotations

from celery import Celery

from apps.api.core.config import settings

celery_app = Celery(
    "imjan_ai",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    # -- serialisatie --------------------------------------------------------
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Brussels",
    enable_utc=True,
    # -- betrouwbaarheid -----------------------------------------------------
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={
        "visibility_timeout": 3600,
        "max_retries": 3,
        "interval_start": 0,
        "interval_step": 0.5,
        "interval_max": 2.0,
    },
    result_expires=60 * 60 * 24,
    # -- grenzen -------------------------------------------------------------
    task_soft_time_limit=settings.pipeline_soft_time_limit,
    task_time_limit=settings.pipeline_hard_time_limit,
    task_default_retry_delay=30,
    worker_max_tasks_per_child=100,
    task_annotations={
        # Analyse is duur (GPU/CPU); niet meer dan N tegelijk starten.
        "elektro_ai.run_pipeline": {"rate_limit": f"{settings.pipeline_rate_limit}/m"},
        "elektro_ai.resume_pipeline": {"rate_limit": f"{settings.pipeline_rate_limit}/m"},
    },
    # -- periodieke taken ----------------------------------------------------
    beat_schedule={
        "reap-stuck-runs": {
            "task": "elektro_ai.reap_stuck_runs",
            "schedule": float(settings.stale_check_seconds),
        },
    },
)

# Taken in apps/worker/tasks.py registreren zichzelf bij import (lazy:
# autodiscover importeert het moduul pas als de worker of beat start).
celery_app.autodiscover_tasks(["apps.worker"], force=True)
