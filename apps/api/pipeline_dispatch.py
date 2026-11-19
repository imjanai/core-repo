"""Publiceer pipeline-opdrachten zonder de worker te laden."""

from apps.shared.queue import RESUME_PIPELINE, RUN_PIPELINE, celery_app

run_pipeline = celery_app.signature(RUN_PIPELINE)
resume_pipeline = celery_app.signature(RESUME_PIPELINE)
