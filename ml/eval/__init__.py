"""
ml/eval — Golden evaluation benchmark and promotion gate engine.
"""

from ml.eval.metrics import (
    FullEvaluationReport,
    Level1DetectionMetrics,
    Level2CountingMetrics,
    Level3OutcomeMetrics,
    Level4WorkflowMetrics,
    compute_level2_counting,
    compute_level3_outcome,
    compute_level4_workflow,
)
from ml.eval.run_eval import evaluate, load_golden_pairs

__all__ = [
    "FullEvaluationReport",
    "Level1DetectionMetrics",
    "Level2CountingMetrics",
    "Level3OutcomeMetrics",
    "Level4WorkflowMetrics",
    "compute_level2_counting",
    "compute_level3_outcome",
    "compute_level4_workflow",
    "load_golden_pairs",
    "evaluate",
]
