from datetime import timedelta
from unittest.mock import Mock
from uuid import uuid4

from sqlalchemy import create_engine

from apps.shared.database import Base
from apps.worker import tasks
from apps.worker.store import SqlCheckpointStore
from packages.pipeline import PipelineRun, RunState
from packages.schema import Project


def test_worker_resumes_failed_run_and_releases_reservation(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    store = SqlCheckpointStore(engine)
    run = PipelineRun(project_id=str(uuid4()), state=RunState.FAILED)
    store.save(run)
    pipeline = Mock()

    def finish(_ctx, *, store, resume, task_ref):
        assert resume.state == RunState.FAILED
        assert store.claim_resume(resume.run_id, "duplicate", timedelta(minutes=1)) is None
        resume.state = RunState.SUCCEEDED
        store.save(resume)
        return resume

    pipeline.run.side_effect = finish
    monkeypatch.setattr(tasks, "get_engine", lambda: engine)
    monkeypatch.setattr(tasks, "_load_project", lambda *_: Project(id="project"))
    monkeypatch.setattr(tasks, "_set_project_status", Mock())
    monkeypatch.setattr(tasks, "build_default_pipeline", lambda: pipeline)

    result = tasks.resume_pipeline.run(run.run_id)

    assert result["state"] == "succeeded"
    assert "resume_claim_token" not in store.load(run.run_id).payload
    assert tasks.resume_pipeline.run(run.run_id)["state"] == "succeeded"
    pipeline.run.assert_called_once()
