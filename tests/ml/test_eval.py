"""
tests/ml/test_eval.py — Unit tests for evaluation framework and 4-tier metrics engine.
"""

import pytest

from ml.eval.metrics import (
    FullEvaluationReport,
    Level1DetectionMetrics,
    compute_level2_counting,
    compute_level3_outcome,
    compute_level4_workflow,
)
from packages.schema import MaterialLine, Project, Symbol, SymbolType


def test_4_tier_metrics_computation():
    gt = Project(
        symbols=[
            Symbol(type=SymbolType.WANDCONTACTDOOS, x=100, y=100),
            Symbol(type=SymbolType.WANDCONTACTDOOS, x=200, y=200),
            Symbol(type=SymbolType.SCHAKELAAR, x=300, y=300),
        ],
        materials=[
            MaterialLine(symbol_id="s1", symbol_type=SymbolType.WANDCONTACTDOOS, description="WCD", quantity=2, unit_price=10.0, total_price=20.0),
            MaterialLine(symbol_id="s2", symbol_type=SymbolType.SCHAKELAAR, description="SCH", quantity=1, unit_price=8.0, total_price=8.0),
        ],
    )

    pred = Project(
        symbols=[
            Symbol(type=SymbolType.WANDCONTACTDOOS, x=100, y=100),
            Symbol(type=SymbolType.WANDCONTACTDOOS, x=200, y=200),
            # Missing switch!
        ],
        materials=[
            MaterialLine(symbol_id="s1", symbol_type=SymbolType.WANDCONTACTDOOS, description="WCD", quantity=2, unit_price=10.0, total_price=20.0),
        ],
    )

    # Level 2 Counting
    l2 = compute_level2_counting([pred], [gt])
    assert l2.avg_total_count_error == 1.0  # 1 missing switch
    assert l2.perfect_drawings_pct == 0.0

    # Level 3 Outcome (Financial)
    l3 = compute_level3_outcome([pred], [gt])
    assert l3.avg_cost_error_euros == 8.0  # 8 euros difference
    assert l3.gt_total_costs == 28.0
    assert l3.pred_total_costs == 20.0

    # Level 4 Workflow
    l4 = compute_level4_workflow([pred], [gt])
    assert l4.avg_corrections_per_drawing == 1.0

    # Full report formatting
    report = FullEvaluationReport(
        model_version="test-model",
        dataset_version="test-gold",
        level1=Level1DetectionMetrics(mean_map50=0.88),
        level2=l2,
        level3=l3,
        level4=l4,
        promotion_eligible=True,
    )
    md = report.to_markdown()
    assert "Evaluatierapport" in md
    assert "Niveau 1" in md
    assert "Niveau 2" in md
    assert "Niveau 3" in md
    assert "Niveau 4" in md
