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

@pytest.mark.asyncio
async def test_review_corrections_update_symbol_overlay_and_download(client):
    import ezdxf
    from openpyxl import load_workbook

    from apps.shared.models import ProjectRow
    from packages.schema import Symbol, SymbolType

    original = Symbol(type=SymbolType.WANDCONTACTDOOS, x=100, y=200)
    project_id = str(uuid.uuid4())
    async with TestSessionLocal() as db:
        db.add(ProjectRow(
            id=project_id, status=ProjectStatus.DONE.value, file_type="dxf",
            s3_key="uploads/plan.dxf", symbols=[original.model_dump(mode="json")],
        ))
        await db.commit()

    project_url = f"/projects/{project_id}"
    asset = await client.get("/review/")
    assert asset.status_code == 200
    assert "Tekening beoordelen" in asset.text

    doc = ezdxf.new(units=4)
    doc.modelspace().add_line((0, 0), (1000, 500))
    dxf = io.StringIO()
    doc.write(dxf)
    with patch("apps.api.routers.review.download_file", return_value=dxf.getvalue().encode()):
        drawing = await client.get(f"{project_url}/review/drawing")
    assert drawing.status_code == 200
    assert drawing.json() == {"paths": [[[0, 0], [1000, 500]]], "truncated": False}

    response = await client.post(f"{project_url}/corrections?review=true", json={
        "action": "change_type", "symbol_id": original.id,
        "new_type": SymbolType.SCHAKELAAR.value, "new_x": 123, "new_y": 456,
    })
    assert response.status_code == 201, response.text

    overlay = await client.get(f"{project_url}/review/symbols")
    assert overlay.status_code == 200
    assert overlay.json()[0]["type"] == SymbolType.SCHAKELAAR.value
    assert overlay.json()[0]["x"] == 123

    raw = await client.get(project_url)
    assert raw.json()["symbols"][0]["type"] == SymbolType.WANDCONTACTDOOS.value

    materials = await client.get(f"{project_url}/materials?review=true")
    assert materials.status_code == 200
    items = materials.json()["items"]
    assert any(item["symbol_type"] == SymbolType.SCHAKELAAR.value for item in items)
    assert all(item["symbol_type"] != SymbolType.WANDCONTACTDOOS.value for item in items)

    excel = await client.get(f"{project_url}/materials?review=true&format=xlsx")
    assert excel.status_code == 200
    sheet = load_workbook(io.BytesIO(excel.content), read_only=True).active
    assert [row[0] for row in sheet.iter_rows(min_row=2, values_only=True)] == [
        item["description"] for item in items
    ]

@pytest.mark.asyncio
async def test_revision_compares_and_carries_only_clear_corrections(client):
    from apps.shared.models import ProjectRow
    from packages.schema import Symbol, SymbolType

    previous_id, current_id = str(uuid.uuid4()), str(uuid.uuid4())
    attributes = {"block_name": "WCD", "layer": "ELEKTRA"}
    old = Symbol(type=SymbolType.WANDCONTACTDOOS, x=100, y=200, attributes=attributes)
    matched = Symbol(type=old.type, x=102, y=200, attributes=attributes)
    uncertain = Symbol(type=old.type, x=500, y=200, attributes=attributes)
    async with TestSessionLocal() as db:
        for project_id, symbols in [(previous_id, [old, uncertain]), (current_id, [matched])]:
            db.add(ProjectRow(
                id=project_id, status=ProjectStatus.DONE.value, file_type="dxf",
                symbols=[item.model_dump(mode="json") for item in symbols],
            ))
        await db.commit()

    for symbol in (old, uncertain):
        response = await client.post(f"/projects/{previous_id}/corrections?review=true", json={
            "action": "change_type", "symbol_id": symbol.id, "new_type": SymbolType.SCHAKELAAR.value,
        })
        assert response.status_code == 201, response.text

    revision = f"/projects/{current_id}/review/revision"
    params = {"previous_id": previous_id}
    comparison = await client.get(revision, params=params)
    assert comparison.status_code == 200, comparison.text
    assert {change["kind"] for change in comparison.json()["changes"]} == {"retyped", "removed"}
    assert comparison.json()["materials"]

    carry = await client.post(f"{revision}/carry", params=params)
    assert carry.status_code == 200, carry.text
    assert carry.json()["applied"] == 1
    assert [item["id"] for item in carry.json()["needs_review"]] == [uncertain.id]

    overlay = await client.get(f"/projects/{current_id}/review/symbols")
    assert overlay.json()[0]["type"] == SymbolType.SCHAKELAAR.value

    again = await client.post(f"{revision}/carry", params=params)
    assert again.json()["applied"] == 0
    assert again.json()["already_reviewed"] == 1

@pytest.mark.asyncio
async def test_library_filters_literal_names_and_does_not_sign_downloads(client):
    from apps.shared.models import ProjectRow

    async with TestSessionLocal() as db:
        for name, file_type, project_status in [
            ("Plan_100%.dxf", "dxf", "done"),
            ("PlanX100-extra.dxf", "dxf", "done"),
            ("Plan_100%.pdf", "pdf", "done"),
            ("Plan_100% revised.dxf", "dxf", "failed"),
        ]:
            db.add(ProjectRow(name=name, file_type=file_type, status=project_status, s3_key="source"))
        await db.commit()

    with patch("apps.api.routers.projects.generate_presigned_url", new_callable=AsyncMock) as sign:
        result = await client.get("/projects", params={
            "q": "PLAN_100%", "file_type": "dxf", "status": "done",
            "include_download_url": "false", "page_size": 1,
        })
    assert result.status_code == 200, result.text
    assert result.json()["total"] == 1
    assert [project["name"] for project in result.json()["items"]] == ["Plan_100%.dxf"]
    sign.assert_not_awaited()
