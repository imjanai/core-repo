"""SQLAlchemy-basis en synchrone engine voor workerprocessen."""

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

from apps.shared.config import settings


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=1)
def get_sync_engine():
    """Deel één synchrone engine per workerproces."""
    url = settings.database_url.replace("+asyncpg", "+psycopg2")
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
