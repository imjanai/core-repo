"""
apps/api/main.py — FastAPI entrypoint voor de elektro-ai API.

Start met:
    uv run uvicorn apps.api.main:app --reload --port 8080
of via Docker Compose.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.shared.config import settings
from apps.api.core.database import engine, Base
from apps.api.routers import projects, materials, corrections, health, pipeline, review


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tabellen aanmaken bij opstart (development only).
    # In productie doet Alembic de migraties.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="imJan AI — elektrotechniek platform",
    version="0.1.0",
    description=(
        "Analyseert installatietekeningen, genereert materiaallijsten "
        "en maakt installatietekeningen via MCP."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(materials.router, prefix="/projects", tags=["materials"])
app.include_router(corrections.router, prefix="/projects", tags=["corrections"])
app.include_router(pipeline.router, prefix="/projects", tags=["pipeline"])

app.include_router(review.router, tags=["review"])
app.mount(
    "/review",
    StaticFiles(directory=Path(__file__).resolve().parents[1] / "review" / "static", html=True),
    name="review",
)
