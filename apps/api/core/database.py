"""apps/api/core/database.py — async SQLAlchemy engine + sessie-factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.shared.config import settings
from apps.shared.database import Base as Base

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncSession:  # type: ignore[return]
    """FastAPI dependency die een sessie levert en daarna sluit."""
    async with AsyncSessionLocal() as session:
        yield session
