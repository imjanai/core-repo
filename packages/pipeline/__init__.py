"""
packages/pipeline — enterprise-orkestratie voor de analysepipeline.

Snelle start:

    from packages.pipeline import PipelineOptions, StageContext, build_default_pipeline
    from packages.pipeline.checkpoints import InMemoryCheckpointStore

    pipeline = build_default_pipeline()          # de elf stappen uit het README
    pipeline.validate()                          # DAG controleren (gooit DagError)

    ctx = StageContext(
        project=Project(id="p1"),
        payload={"s3_key": "uploads/plan.dxf", "filename": "plan.dxf"},
        loader=my_s3_loader,                     # -> bytes
        options=PipelineOptions(strict=False),
    )
    run = pipeline.run(ctx, store=InMemoryCheckpointStore())
    print(run.state, run.progress, ctx.project.materials)

Gedrag dat je mag verwachten:
  * `PipelineFailed` als een verplichte stap definitief faalt;
  * `PipelineAlreadyRunning` als er al een lopende run voor het project is;
  * `PipelineCancelled` na `ctx.request_cancel(...)`;
  * bij hervatten (`resume=run_id`) draaien alleen de stappen die nog niet klaar waren.
"""

from __future__ import annotations

from packages.pipeline.checkpoints import (
    CheckpointStore,
    FileCheckpointStore,
    InMemoryCheckpointStore,
)
from packages.pipeline.engine import Pipeline, run_once
from packages.pipeline.errors import (
    DagError,
    PipelineAlreadyRunning,
    PipelineCancelled,
    PipelineError,
    PipelineFailed,
    NotImplementedStage,
    PermanentStageError,
    RetryableStageError,
    StageSkipped,
    StageTimeoutError,
)
from packages.pipeline.events import (
    CallbackHandler,
    CollectingHandler,
    EventBus,
    LoggingHandler,
)
from packages.pipeline.fusion import FusionConfig, FusionStats, fuse, point_in_polygon
from packages.pipeline.metrics import InMemoryMetrics, LoggingMetrics, NullMetrics
from packages.pipeline.stage import (
    NullSink,
    PipelineOptions,
    ResultSink,
    SourceLoader,
    Stage,
    StageContext,
    stage,
)
from packages.pipeline.stages import DEFAULT_STAGES, build_default_pipeline, detect_file_type
from packages.pipeline.exporters import (
    export_materials_excel,
    export_project_dxf,
    export_quote_pdf,
)
from packages.pipeline.types import (
    EventType,
    NO_RETRY,
    FAST_RETRY,
    PipelineEvent,
    PipelineRun,
    RetryPolicy,
    RunState,
    StageResult,
    StageState,
)

__all__ = [
    "Pipeline",
    "run_once",
    "Stage",
    "StageContext",
    "stage",
    "PipelineOptions",
    "ResultSink",
    "SourceLoader",
    "NullSink",
    "build_default_pipeline",
    "DEFAULT_STAGES",
    "detect_file_type",
    "export_materials_excel",
    "export_quote_pdf",
    "export_project_dxf",
    "fuse",
    "FusionConfig",
    "FusionStats",
    "point_in_polygon",
    "EventBus",
    "LoggingHandler",
    "CollectingHandler",
    "CallbackHandler",
    "PipelineEvent",
    "EventType",
    "PipelineRun",
    "StageResult",
    "RunState",
    "StageState",
    "RetryPolicy",
    "NO_RETRY",
    "FAST_RETRY",
    "CheckpointStore",
    "InMemoryCheckpointStore",
    "FileCheckpointStore",
    "InMemoryMetrics",
    "LoggingMetrics",
    "NullMetrics",
    "PipelineError",
    "PipelineFailed",
    "PipelineCancelled",
    "PipelineAlreadyRunning",
    "DagError",
    "PermanentStageError",
    "RetryableStageError",
    "StageTimeoutError",
    "StageSkipped",
    "NotImplementedStage",
]
