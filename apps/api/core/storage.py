"""apps/api/core/storage.py — S3-compatibele opslag (MinIO / AWS S3)."""

import asyncio
import functools
import mimetypes
import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from apps.api.core.config import settings


def _make_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )


# Boto3 is synchroon; we draaien het in een thread-pool zodat FastAPI niet blokkeert.

async def upload_file(data: bytes, original_filename: str) -> str:
    """Upload bytes naar S3 en geef de S3-key terug."""
    ext = Path(original_filename).suffix.lower()
    key = f"uploads/{uuid.uuid4()}{ext}"
    content_type = mimetypes.guess_type(original_filename)[0] or "application/octet-stream"

    loop = asyncio.get_running_loop()
    client = _make_client()

    await loop.run_in_executor(
        None,
        functools.partial(
            client.put_object,
            Bucket=settings.s3_bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        ),
    )
    return key


async def generate_presigned_url(key: str, expires: int = 3600) -> str:
    """Genereer een tijdelijke download-URL."""
    loop = asyncio.get_running_loop()
    client = _make_client()

    url: str = await loop.run_in_executor(
        None,
        functools.partial(
            client.generate_presigned_url,
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=expires,
        ),
    )
    return url


async def ensure_bucket_exists() -> None:
    """Maak de bucket aan als die nog niet bestaat (handig voor lokale MinIO)."""
    loop = asyncio.get_running_loop()
    client = _make_client()

    def _create():
        try:
            client.head_bucket(Bucket=settings.s3_bucket)
        except ClientError:
            client.create_bucket(Bucket=settings.s3_bucket)

    await loop.run_in_executor(None, _create)
