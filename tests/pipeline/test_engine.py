"""
tests/pipeline/test_engine.py — dekking van de orkestratielaag.

Draaien:
    uv run pytest tests/pipeline/ -v
"""

from __future__ import annotations

import time

import pytest

from packages.pipeline import (
    CollectingHandler,
    DagError,
    EventBus,
    EventType,
    InMemoryCheckpointStore,
    InMemoryMetrics,
    NO_RETRY,
    Pipeline,
    PipelineAlreadyRunning,
    PipelineCancelled,
    PipelineFailed,
    PipelineOptions,
    PermanentStageError,
    RetryPolicy,
    RetryableStageError,
    StageContext,
    StageResult,
    StageState,
    RunState,
    StageTimeoutError,
    stage,
)
from packages.schema import Project


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_ctx(**kwargs) -> StageContext:
    project = kwargs.pop("project", None) or Project(id="p-test")
    return StageContext(
        project=project,
        options=kwargs.pop("options", None) or PipelineOptions(default_retry=NO_RETRY),
        payload=kwargs.pop("payload", None) or {},
        events=kwargs.pop("events", None) or EventBus(),
        metrics=kwargs.pop("metrics", None) or InMemoryMetrics(),
        **kwargs,
    )


def pipeline(*stages) -> Pipeline:
    return Pipeline(name="test", stages=list(stages))


# ---------------------------------------------------------------------------
# DAG
# ---------------------------------------------------------------------------


def test_duplicate_stage_id_rejected():
    a = stage(id="a")(lambda ctx: None)
    b = stage(id="a")(lambda ctx: None)
    with pytest.raises(DagError, match="Dubbele stage-id"):
        pipeline(a, b).validate()


def test_unknown_dependency_rejected():
    a = stage(id="a", requires=("bestaat_niet",))(lambda ctx: None)
    with pytest.raises(DagError, match="onbekende stage"):
        pipeline(a).validate()


def test_self_dependency_rejected():
    a = stage(id="a", requires=("a",))(lambda ctx: None)
    with pytest.raises(DagError):
        pipeline(a).validate()


def test_cycle_rejected():
    a = stage(id="a", requires=("b",))(lambda ctx: None)
    b = stage(id="b", requires=("a",))(lambda ctx: None)
    with pytest.raises(DagError, match="Cirkel"):
        pipeline(a, b).validate()


def test_topological_order():
    """Stappen mogen in willekeurige volgorde gedeclareerd worden."""
    out = stage(id="out", requires=("fuse",))(lambda ctx: None)
    fuse = stage(id="fuse", requires=("ingest",))(lambda ctx: None)
    ingest = stage(id="ingest")(lambda ctx: None)
    p = pipeline(out, fuse, ingest)
    assert p.order == ["ingest", "fuse", "out"]


def test_describe_lists_every_stage():
    a = stage(id="a", name="Eerste", requires=())(lambda ctx: None)
    b = stage(id="b", requires=("a",))(lambda ctx: None)
    described = pipeline(a, b).describe()
    assert [d["id"] for d in described] == ["a", "b"]
    assert described[0]["name"] == "Eerste"
    assert described[1]["requires"] == ["a"]


# ---------------------------------------------------------------------------
# Retry / foutbehandeling
# ---------------------------------------------------------------------------


def test_retryable_error_is_retried_until_success():
    calls = {"n": 0}

    @stage(
        id="flaky",
        retry=RetryPolicy(max_attempts=4, base_delay=0, jitter=False),
    )
    def flaky(ctx: StageContext) -> None:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RetryableStageError("S3 503")

    bus = EventBus()
    collector = bus.subscribe(CollectingHandler())
    metrics = InMemoryMetrics()

    run = pipeline(flaky).run(make_ctx(events=bus, metrics=metrics))

    assert run.state == RunState.SUCCEEDED
    assert run.stage("flaky").attempts == 3
    assert calls["n"] == 3
    assert metrics.total_retries == 2
    assert len(collector.of(EventType.STAGE_RETRYING)) == 2
    assert collector.stages == ["flaky"]


def test_permanent_error_fails_immediately_without_retry():
    calls = {"n": 0}

    @stage(id="bad", retry=RetryPolicy(max_attempts=5, base_delay=0, jitter=False))
    def bad(ctx: StageContext) -> None:
        calls["n"] += 1
        raise PermanentStageError("onbekend formaat")

    bus = EventBus()
    collector = bus.subscribe(CollectingHandler())

    with pytest.raises(PipelineFailed) as excinfo:
        pipeline(bad).run(make_ctx(events=bus))

    assert calls["n"] == 1
    assert excinfo.value.stage_id == "bad"
    assert excinfo.value.attempts == 1
    failed = collector.of(EventType.RUN_FAILED)
    assert len(failed) == 1
    assert "onbekend formaat" in failed[0].message


def test_retries_exhausted_marks_run_failed():
    store = InMemoryCheckpointStore()

    @stage(id="always_bad", retry=RetryPolicy(max_attempts=3, base_delay=0, jitter=False))
    def always_bad(ctx: StageContext) -> None:
        raise RetryableStageError("netwerk down")

    ctx = make_ctx()
    with pytest.raises(PipelineFailed, match="netwerk down"):
        pipeline(always_bad).run(ctx, store=store)

    saved = store.load(ctx.run.run_id)
    assert saved.state == RunState.FAILED
    assert saved.stage("always_bad").attempts == 3
    assert saved.stage("always_bad").state == StageState.FAILED


def test_stage_timeout_is_retryable_and_reported():
    @stage(id="slow", retry=NO_RETRY, timeout_s=0.2)
    def slow(ctx: StageContext) -> None:
        time.sleep(1.0)

    with pytest.raises(PipelineFailed) as excinfo:
        pipeline(slow).run(make_ctx())

    assert isinstance(excinfo.value.cause, StageTimeoutError)
    assert "tijdslimiet" in str(excinfo.value)


def test_failure_of_required_stage_stops_later_stages():
    ran: list[str] = []

    @stage(id="first")
    def first(ctx: StageContext) -> None:
        raise PermanentStageError("stop")

    @stage(id="second", requires=("first",))
    def second(ctx: StageContext) -> None:
        ran.append("second")

    with pytest.raises(PipelineFailed):
        pipeline(first, second).run(make_ctx())

    assert ran == []


# ---------------------------------------------------------------------------
# Optionele stappen / degradatie
# ---------------------------------------------------------------------------


def test_optional_stage_skipped_when_implementation_missing():
    @stage(id="vision", optional=True)
    def vision(ctx: StageContext) -> None:
        raise ModuleNotFoundError("No module named 'torch'")

    @stage(id="after", requires=("vision",))
    def after(ctx: StageContext) -> None:
        ctx.project.meta["after"] = True

    run = pipeline(vision, after).run(make_ctx())

    assert run.state == RunState.SUCCEEDED
    assert run.stage("vision").state == StageState.SKIPPED
    assert "torch" in run.stage("vision").error
    assert run.stage("after").state == StageState.SUCCEEDED


def test_optional_stage_failure_continues_unless_strict():
    @stage(id="vision", optional=True, retry=NO_RETRY)
    def vision(ctx: StageContext) -> None:
        raise RetryableStageError("vLLM 503 na 4 pogingen")

    @stage(id="after", requires=("vision",))
    def after(ctx: StageContext) -> None:
        ctx.project.meta["after"] = True

    # normaal: degraded doorgaan
    run = pipeline(vision, after).run(make_ctx())
    assert run.state == RunState.SUCCEEDED
    assert run.stage("vision").state == StageState.FAILED

    # strict: alsnog de run kapotmaken
    strict = PipelineOptions(strict=True, default_retry=NO_RETRY)
    with pytest.raises(PipelineFailed):
        pipeline(vision, after).run(make_ctx(options=strict))


def test_ctx_skip_marks_stage_skipped():
    @stage(id="maybe")
    def maybe(ctx: StageContext) -> None:
        ctx.skip("geen vectorbron (image)")

    run = pipeline(maybe).run(make_ctx())
    assert run.stage("maybe").state == StageState.SKIPPED
    assert "geen vectorbron" in run.stage("maybe").error


def test_when_condition_gates_stage():
    executed: list[str] = []

    @stage(id="vlm", when=lambda ctx: ctx.options.get("vlm_enabled", True))
    def vlm(ctx: StageContext) -> None:
        executed.append("vlm")

    run = pipeline(vlm).run(make_ctx(options=PipelineOptions(default_retry=NO_RETRY)))
    assert run.stage("vlm").state == StageState.SUCCEEDED
    assert executed == ["vlm"]

    opts = PipelineOptions(default_retry=NO_RETRY, extra={"vlm_enabled": False})
    run2 = pipeline(vlm).run(make_ctx(options=opts))
    assert run2.stage("vlm").state == StageState.SKIPPED
    assert executed == ["vlm"]


# ---------------------------------------------------------------------------
# Checkpoints, hervatten en idempotentie
# ---------------------------------------------------------------------------


def test_checkpoint_written_after_every_stage():
    store = InMemoryCheckpointStore()

    @stage(id="one")
    def one(ctx: StageContext) -> None:
        ctx.project.meta["one"] = True

    @stage(id="two", requires=("one",))
    def two(ctx: StageContext) -> None:
        ctx.project.meta["two"] = True

    run = pipeline(one, two).run(make_ctx(), store=store)

    saved = store.load(run.run_id)
    assert saved is not None
    assert saved.state == RunState.SUCCEEDED
    assert saved.project_snapshot["meta"]["two"] is True
    # minstens 1 checkpoint voor start + 1 per stage + 1 voor succes
    assert store.save_count >= 4


def test_resume_skips_completed_stages_and_finishes():
    store = InMemoryCheckpointStore()
    calls = {"one": 0, "two": 0}

    @stage(id="one")
    def one(ctx: StageContext) -> None:
        calls["one"] += 1
        ctx.project.meta["one"] = calls["one"]

    @stage(id="two", requires=("one",), retry=NO_RETRY)
    def two(ctx: StageContext) -> None:
        calls["two"] += 1
        if calls["two"] == 1:
            raise PermanentStageError("tijdelijk kapot")

    p = pipeline(one, two)
    ctx = make_ctx()
    with pytest.raises(PipelineFailed):
        p.run(ctx, store=store)

    failed_run = store.load(ctx.run.run_id)
    assert failed_run.state == RunState.FAILED
    assert calls == {"one": 1, "two": 1}

    # Hervatten: 'one' opnieuw? Nee — alleen 'two'.
    resume_ctx = make_ctx()
    run = p.run(resume_ctx, store=store, resume=failed_run.run_id)

    assert run.state == RunState.SUCCEEDED
    assert calls == {"one": 1, "two": 2}
    assert run.stage("one").attempts == 1
    assert run.stage("two").attempts == 1


def test_resume_restores_project_snapshot():
    store = InMemoryCheckpointStore()
    calls = {"n": 0}

    @stage(id="seed")
    def seed(ctx: StageContext) -> None:
        ctx.project.meta["seeded"] = "ja"
        ctx.project.scale = 2.5

    @stage(id="boom", requires=("seed",), retry=NO_RETRY)
    def boom(ctx: StageContext) -> None:
        assert ctx.project.meta["seeded"] == "ja"  # snapshot werkt
        calls["n"] += 1
        if calls["n"] == 1:
            raise PermanentStageError("kapot")

    p = pipeline(seed, boom)
    ctx = make_ctx()
    with pytest.raises(PipelineFailed):
        p.run(ctx, store=store)

    resume_ctx = make_ctx(project=Project(id="p-test"))  # leeg project!
    run = p.run(resume_ctx, store=store, resume=ctx.run.run_id)

    assert run.state == RunState.SUCCEEDED
    assert resume_ctx.project.meta["seeded"] == "ja"
    assert resume_ctx.project.scale == 2.5


def test_replay_stage_runs_again_on_resume():
    store = InMemoryCheckpointStore()
    calls = {"n": 0}

    @stage(id="ingest", replay=True)
    def ingest(ctx: StageContext) -> None:
        calls["n"] += 1

    @stage(id="boom", requires=("ingest",), retry=NO_RETRY)
    def boom(ctx: StageContext) -> None:
        if calls["n"] < 2:
            raise PermanentStageError("eerste poging faalt")
        ctx.project.meta["ok"] = True

    p = pipeline(ingest, boom)
    ctx = make_ctx()
    with pytest.raises(PipelineFailed):
        p.run(ctx, store=store)

    run = p.run(make_ctx(), store=store, resume=ctx.run.run_id)
    assert run.state == RunState.SUCCEEDED
    assert calls["n"] == 2  # ingest is replay → opnieuw gedraaid


def test_two_concurrent_runs_for_one_project_are_blocked():
    store = InMemoryCheckpointStore()

    @stage(id="one")
    def one(ctx: StageContext) -> None:
        pass

    p = pipeline(one)
    ctx = make_ctx()
    p.run(ctx, store=store)  # slaagt → terminal

    # Forceer een niet-terminal run in de store
    from packages.pipeline import PipelineRun

    open_run = PipelineRun(project_id="p-test", state=RunState.RUNNING)
    store.save(open_run)

    with pytest.raises(PipelineAlreadyRunning) as excinfo:
        p.run(make_ctx(), store=store)
    assert excinfo.value.run.run_id == open_run.run_id


def test_idempotency_key_returns_previous_success():
    store = InMemoryCheckpointStore()

    @stage(id="one")
    def one(ctx: StageContext) -> None:
        ctx.project.meta["runs"] = ctx.project.meta.get("runs", 0) + 1

    p = pipeline(one)
    first = p.run(make_ctx(), store=store, idempotency_key="upload-1")
    second = p.run(make_ctx(), store=store, idempotency_key="upload-1")

    assert first.run_id == second.run_id
    assert second.state == RunState.SUCCEEDED


# ---------------------------------------------------------------------------
# Annuleren
# ---------------------------------------------------------------------------


def test_cancel_stops_run_before_next_stage():
    ran: list[str] = []

    @stage(id="one")
    def one(ctx: StageContext) -> None:
        ctx.request_cancel("operator stopte de run")

    @stage(id="two", requires=("one",))
    def two(ctx: StageContext) -> None:
        ran.append("two")

    bus = EventBus()
    collector = bus.subscribe(CollectingHandler())

    with pytest.raises(PipelineCancelled):
        pipeline(one, two).run(make_ctx(events=bus))

    assert ran == []
    assert len(collector.of(EventType.RUN_CANCELLED)) == 1


# ---------------------------------------------------------------------------
# Events & metriek
# ---------------------------------------------------------------------------


def test_event_sequence_for_successful_run():
    bus = EventBus()
    collector = bus.subscribe(CollectingHandler())

    @stage(id="one")
    def one(ctx: StageContext) -> None:
        pass

    @stage(id="two", requires=("one",))
    def two(ctx: StageContext) -> None:
        pass

    run = pipeline(one, two).run(make_ctx(events=bus))

    types = [e.type for e in collector.events]
    assert types[0] == EventType.RUN_STARTED
    assert types[-1] == EventType.RUN_SUCCEEDED
    assert types.index(EventType.STAGE_STARTED) < types.index(EventType.STAGE_SUCCEEDED)
    assert collector.stages == ["one", "two"]
    assert run.progress == 1.0


def test_metrics_record_durations_and_outcomes():
    metrics = InMemoryMetrics()

    @stage(id="one")
    def one(ctx: StageContext) -> None:
        pass

    pipeline(one).run(make_ctx(metrics=metrics))

    assert metrics.counter("pipeline.stage.outcome", stage="one", outcome="succeeded") == 1
    assert metrics.last_timing("pipeline.stage.duration", stage="one",
                               outcome="succeeded") is not None
    assert metrics.last_timing("pipeline.run.duration", outcome="succeeded") is not None


def test_broken_event_handler_does_not_break_run():
    """Observability mag de analyse niet platleggen."""

    def exploding(_event) -> None:
        raise RuntimeError("monitoring kapot")

    bus = EventBus([exploding])
    bus.subscribe(CollectingHandler())

    @stage(id="one")
    def one(ctx: StageContext) -> None:
        pass

    run = pipeline(one).run(make_ctx(events=bus))
    assert run.state == RunState.SUCCEEDED


def test_stage_result_shape_for_api():
    @stage(id="one", name="Eerste stap", description="uitleg")
    def one(ctx: StageContext) -> None:
        pass

    run = pipeline(one).run(make_ctx())
    result: StageResult = run.stage("one")
    assert result.name == "Eerste stap"
    assert result.state == StageState.SUCCEEDED
    assert result.attempts == 1
    assert result.finished_at is not None
    assert 0 <= run.progress <= 1
