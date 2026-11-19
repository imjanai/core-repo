"""
apps/worker/loader.py — de twee randen van de pipeline.

Aan de linkerkant: `S3SourceLoader` haalt het geüploade bestand op.
Aan de rechterkant: `ProjectResultSink` schrijft het eindresultaat weg.

Beide leven buiten `packages/pipeline` omdat het pakket bewust geen kennis
heeft van boto3 of SQLAlchemy-sessies — daardoor is de engine in tests te
draaien zonder netwerk of database.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from apps.api.core.config import settings
from apps.api.models.db import ProjectRow
from packages.pipeline.stage import ResultSink
from packages.pipeline.types import PipelineRun
from packages.schema import FileType, Project, ProjectStatus

logger = logging.getLogger("imjan.worker")


class S3SourceLoader:
    """
    Leest objecten uit S3-compatibele opslag (MinIO of AWS).

    De client wordt pas bij het eerste gebruik gemaakt: de worker start ook
    als de opslag tijdelijk onbereikbaar is, en een gefaalde taak krijgt
    daardoor een normale retry in plaats van een import-fout bij opstarten.
    """

    def __init__(self, bucket: str | None = None) -> None:
        self.bucket = bucket or settings.s3_bucket
        self._client = None

    def _client_or_create(self):
        if self._client is None:
            import boto3  # trage, zware import → lazy

            self._client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
            )
        return self._client

    def load(self, key: str) -> bytes:
        client = self._client_or_create()
        obj = client.get_object(Bucket=self.bucket, Key=key)
        data: bytes = obj["Body"].read()
        if not data:
            raise ValueError(f"Object {key} in bucket {self.bucket} is leeg.")
        return data


class ProjectResultSink(ResultSink):
    """
    Schrijft het succesvolle analyse-resultaat in `projects`.

    De worker gebruikt een synchrone sessie; de API leest hetzelfde record
    asynchroon terug. Eén schrijfactie aan het eind — niet per stage — zodat
    de frontend nooit een half gevuld project ziet.
    """

    def __init__(self, engine, project_id: str) -> None:
        self.engine = engine
        self.project_id = project_id

    def publish(self, run: PipelineRun, project: Project) -> None:
        with Session(self.engine) as session:
            row = session.get(ProjectRow, self.project_id)
            if row is None:
                logger.warning(
                    "Project %s bestaat niet meer; resultaat niet weggeschreven.",
                    self.project_id,
                )
                return

            row.status = ProjectStatus.DONE.value
            row.scale = project.scale
            row.rooms = [r.model_dump(mode="json") for r in project.rooms]
            row.symbols = [s.model_dump(mode="json") for s in project.symbols]
            row.materials = [m.model_dump(mode="json") for m in project.materials]
            row.warnings = [w.model_dump(mode="json") for w in project.warnings]
            row.meta = {**(project.meta or {}), "run_id": run.run_id}
            if project.file_type != FileType.UNKNOWN:
                row.file_type = project.file_type.value
            session.commit()

        logger.info(
            "Project %s opgeleverd: %d symbolen, %d materialen, %d waarschuwingen",
            self.project_id,
            len(project.symbols),
            len(project.materials),
            len(project.warnings),
        )
