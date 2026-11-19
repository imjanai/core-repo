"""
tests/api/test_projects.py — integratietests voor de projects-router.

Gebruik een in-memory SQLite-database (geen PostgreSQL nodig).
Celery-taken worden gemockt met unittest.mock.

Draaien:
    uv run pytest tests/api/ -v
"""

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.core.database import Base, get_db
from apps.api.main import app
from apps.api.models.db import PipelineRunRow, run_to_row
from packages.pipeline import PipelineRun, RunState, StageResult, StageState
from packages.schema import ProjectStatus

# ---------------------------------------------------------------------------
# Test-database (SQLite in-memory)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
@patch("apps.api.routers.projects.upload_file", new_callable=AsyncMock)
@patch("apps.api.routers.projects.run_pipeline")
async def test_create_project(mock_task, mock_upload, client):
    mock_upload.return_value = "uploads/test.dxf"
    mock_celery_result = MagicMock()
    mock_celery_result.id = str(uuid.uuid4())
    mock_task.delay.return_value = mock_celery_result

    file_content = b"SECTION\n0\nHEADER\n"  # minimale DXF-stub
    resp = await client.post(
        "/projects",
        files={"file": ("plattegrond.dxf", io.BytesIO(file_content), "application/octet-stream")},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == ProjectStatus.PROCESSING.value
    assert data["file_type"] == "dxf"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_project_not_found(client):
    resp = await client.get(f"/projects/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
@patch("apps.api.routers.projects.upload_file", new_callable=AsyncMock)
@patch("apps.api.routers.projects.run_pipeline")
async def test_list_projects(mock_task, mock_upload, client):
    mock_upload.return_value = "uploads/test.dxf"
    mock_task.delay.return_value = MagicMock(id=str(uuid.uuid4()))

    # Upload 3 projecten
    for _ in range(3):
        await client.post(
            "/projects",
            files={"file": ("plan.dxf", io.BytesIO(b"0\nSECTION"), "application/octet-stream")},
        )

    resp = await client.get("/projects?page=1&page_size=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


@pytest.mark.asyncio
@patch("apps.api.routers.projects.upload_file", new_callable=AsyncMock)
@patch("apps.api.routers.projects.run_pipeline")
async def test_delete_project(mock_task, mock_upload, client):
    mock_upload.return_value = "uploads/test.dxf"
    mock_task.delay.return_value = MagicMock(id=str(uuid.uuid4()))

    create = await client.post(
        "/projects",
        files={"file": ("plan.dxf", io.BytesIO(b"0"), "application/octet-stream")},
    )
    project_id = create.json()["id"]

    del_resp = await client.delete(f"/projects/{project_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/projects/{project_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
@patch("apps.api.routers.projects.upload_file", new_callable=AsyncMock)
@patch("apps.api.routers.projects.run_pipeline")
async def test_add_correction(mock_task, mock_upload, client):
    mock_upload.return_value = "uploads/test.dxf"
    mock_task.delay.return_value = MagicMock(id=str(uuid.uuid4()))

    create = await client.post(
        "/projects",
        files={"file": ("plan.dxf", io.BytesIO(b"0"), "application/octet-stream")},
    )
    project_id = create.json()["id"]

    correction = {
        "action": "add",
        "new_type": "wandcontactdoos",
        "new_x": 1200.0,
        "new_y": 800.0,
        "comment": "Extra contactdoos vergeten",
    }
    resp = await client.post(f"/projects/{project_id}/corrections", json=correction)
    assert resp.status_code == 201
    body = resp.json()
    assert body["action"] == "add"
    assert body["new_type"] == "wandcontactdoos"


@pytest.mark.asyncio
@patch("apps.api.routers.projects.upload_file", new_callable=AsyncMock)
@patch("apps.api.routers.projects.run_pipeline")
async def test_add_correction_validation(mock_task, mock_upload, client):
    """action=add zonder new_type moet 422 geven."""
    mock_upload.return_value = "uploads/test.dxf"
    mock_task.delay.return_value = MagicMock(id=str(uuid.uuid4()))

    create = await client.post(
        "/projects",
        files={"file": ("plan.dxf", io.BytesIO(b"0"), "application/octet-stream")},
    )
    project_id = create.json()["id"]

    resp = await client.post(
        f"/projects/{project_id}/corrections",
        json={"action": "add", "new_x": 100.0, "new_y": 200.0},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Pipeline-voortgang en hervatten
# ---------------------------------------------------------------------------


async def seed_pipeline_run(project_id: str, state: RunState, **kwargs) -> str:
    """
    Zet een run rechtstreeks in de test-DB, alsof de worker hem heeft
    weggeschreven. Zo testen we de lees-/herstelpaden zonder Celery.
    """
    run = PipelineRun(
        project_id=project_id,
        pipeline="analyse",
        state=state,
        stages=[
            StageResult(stage_id="ingest", name="Ingest",
                        state=StageState.SUCCEEDED, attempts=1, duration_ms=12),
            StageResult(stage_id="fuse", name="Fusie",
                        state=StageState.RUNNING, attempts=1),
        ],
        **kwargs,
    )
    async with TestSessionLocal() as session:
        row = PipelineRunRow(run_id=run.run_id, project_id=project_id)
        run_to_row(run, row)
        session.add(row)
        await session.commit()
    return run.run_id


@pytest.mark.asyncio
async def test_pipeline_detail_zonder_run_geeft_404(client):
    resp = await client.get(f"/projects/{uuid.uuid4()}/pipeline")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pipeline_detail_toont_stappen(client):
    project_id = str(uuid.uuid4())
    run_id = await seed_pipeline_run(
        project_id, RunState.RUNNING, current_stage="fuse"
    )

    resp = await client.get(f"/projects/{project_id}/pipeline")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == run_id
    assert body["state"] == "running"
    assert body["current_stage"] == "fuse"
    assert body["progress"] == 0.5  # 1 van de 2 stappen klaar
    assert [s["stage_id"] for s in body["stages"]] == ["ingest", "fuse"]
    assert body["stages"][0]["state"] == "succeeded"
    assert body["stages"][1]["attempts"] == 1

    # zelfde run ook in de historie
    runs = await client.get(f"/projects/{project_id}/pipeline/runs")
    assert runs.status_code == 200
    assert [r["run_id"] for r in runs.json()["items"]] == [run_id]


@pytest.mark.asyncio
async def test_resume_geslaagde_run_geeft_conflict(client):
    project_id = str(uuid.uuid4())
    await seed_pipeline_run(project_id, RunState.SUCCEEDED)

    resp = await client.post(f"/projects/{project_id}/pipeline/resume")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_resume_lopende_run_geeft_conflict(client):
    """Verse, nog niet-gestrande run → er loopt al iets, niet nog eens."""
    project_id = str(uuid.uuid4())
    await seed_pipeline_run(project_id, RunState.RUNNING)

    resp = await client.post(f"/projects/{project_id}/pipeline/resume")
    assert resp.status_code == 409


@pytest.mark.asyncio
@patch("apps.api.routers.pipeline.resume_pipeline")
async def test_resume_mislukte_run_wordt_opnieuw_gepland(mock_task, client):
    mock_task.delay.return_value = MagicMock(id="celery-task-42")
    project_id = str(uuid.uuid4())
    run_id = await seed_pipeline_run(
        project_id, RunState.FAILED, error="vLLM onbereikbaar", current_stage="vlm"
    )

    resp = await client.post(f"/projects/{project_id}/pipeline/resume")
    assert resp.status_code == 202
    body = resp.json()
    assert body["run_id"] == run_id
    assert body["task_id"] == "celery-task-42"
    assert body["state"] == "queued"
    mock_task.delay.assert_called_once_with(run_id)
