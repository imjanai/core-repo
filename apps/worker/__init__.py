"""
apps/worker — de Celery-worker die de analysepipeline uitvoert.

    uv run celery -A apps.worker.celery_app worker --loglevel=info

De eigenlijke stappen staan in `packages.pipeline`; deze app zorgt voor de
dingen eromheen: broker, database-checkpoints, S3-toegang, statussen en
herstel na een crash.
"""
