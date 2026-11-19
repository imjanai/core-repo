"""Celery-configuratie en taaknamen voor producenten en workers."""

from __future__ import annotations

from celery import Celery

from apps.shared.config import settings

RUN_PIPELINE = "elektro_ai.run_pipeline"
RESUME_PIPELINE = "elektro_ai.resume_pipeline"
REAP_STUCK_RUNS = "elektro_ai.reap_stuck_runs"

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
        RUN_PIPELINE: {"rate_limit": f"{settings.pipeline_rate_limit}/m"},
        RESUME_PIPELINE: {"rate_limit": f"{settings.pipeline_rate_limit}/m"},
    },
    # -- periodieke taken ----------------------------------------------------
    beat_schedule={
        "reap-stuck-runs": {
            "task": REAP_STUCK_RUNS,
            "schedule": float(settings.stale_check_seconds),
        },
    },
)
