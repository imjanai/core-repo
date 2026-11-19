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

from apps.shared.queue import celery_app as celery_app

celery_app.autodiscover_tasks(["apps.worker"], force=True)
