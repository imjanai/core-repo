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
from ml.eval.run_eval import load_golden_pairs
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
        level1=Level1DetectionMetrics(),
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


def test_golden_set_preserves_dxf_filename(tmp_path):
    drawings = tmp_path / "tekeningen"
    answers = tmp_path / "antwoorden"
    drawings.mkdir()
    answers.mkdir()
    (drawings / "plan-01.dxf").write_bytes(b"drawing")
    expected = Project(name="plan-01")
    (answers / "plan-01.json").write_text(expected.model_dump_json(), encoding="utf-8")

    assert load_golden_pairs(tmp_path) == [(b"drawing", expected, "plan-01.dxf")]

def test_point_matches_are_one_to_one_and_distinguish_wrong_types():
    from ml.eval.detection import record_drawing

    def symbol(x, kind=SymbolType.WANDCONTACTDOOS):
        return Symbol(type=kind, x=x, y=0)

    expected = [symbol(0), symbol(10), symbol(30), symbol(60)]
    predictions = [symbol(4), symbol(-3), symbol(30, SymbolType.SCHAKELAAR), symbol(90)]
    metrics = Level1DetectionMetrics()
    record_drawing(metrics, "test.png", predictions, expected, 6, detector="test", vlm="disabled")

    assert metrics.overall.correct == 2
    assert metrics.overall.f1 == 0.5
    assert metrics.by_class["wandcontactdoos"].precision == 2 / 3
    assert metrics.by_class["schakelaar"].correct == 0
    result = metrics.drawings[0]
    assert [item["x"] for item in result.misses] == [60]
    assert [item["x"] for item in result.false_positives] == [90]
    assert result.wrong_types[0]["predicted"]["type"] == "schakelaar"
    assert result.corrections == 3


def test_evaluator_uses_raster_calibration_and_measured_scores(monkeypatch):
    from ml.eval import run_eval

    expected = Project(scale=10, symbols=[Symbol(type=SymbolType.WANDCONTACTDOOS, x=100, y=200)])

    def predict(data, filename, vlm_enabled, *, raster_scale):
        assert filename == "test.png" and raster_scale == 10
        return Project(symbols=[Symbol(type=SymbolType.WANDCONTACTDOOS, x=160, y=200)])

    monkeypatch.setattr(run_eval, "run_pipeline_on_image", predict)
    report = run_eval.evaluate("fixture", [(b"image", expected, "test.png")], {
        "evaluation": {"raster_tolerance_px": 6},
    })
    assert report.level1.overall.f1 == 1
    assert report.level1.drawings[0].tolerance == 60
    assert report.level4.avg_corrections_per_drawing == 0

def test_verified_crop_export_groups_revisions_and_excludes_holdout(tmp_path):
    import json

    from PIL import Image

    from ml.data.split import hash_project_split
    from ml.feedback.export_crops import export_crops
    from packages.schema import FileType

    entries = []
    for index, (family, consent) in enumerate([
        ("work-1", True), ("work-1", True), ("held-out", True), ("no-consent", False),
    ]):
        image = Image.new("RGB", (32, 32), (index * 40, 0, 0))
        image.save(tmp_path / f"drawing-{index}.png")
        annotations = Project(
            file_type=FileType.IMAGE, scale=10,
            symbols=[Symbol(type=SymbolType.WANDCONTACTDOOS, x=20, y=30)],
        )
        (tmp_path / f"answer-{index}.json").write_text(annotations.model_dump_json(), encoding="utf-8")
        entries.append({
            "drawing": f"drawing-{index}.png", "reviewed": f"answer-{index}.json",
            "project_family": family, "allow_training": consent,
        })
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"drawings": entries, "golden_families": ["held-out"]}), encoding="utf-8")

    output = tmp_path / "crops"
    stats = export_crops(manifest, output, crop_size=16)

    split = hash_project_split("work-1")
    assert stats[split] == 2 and stats["withheld"] == 2
    records = [json.loads(line) for line in (output / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2 and all(record["project_family"] == "work-1" for record in records)
    with Image.open(records[1]["image"]) as crop:
        assert crop.size == (16, 16)
        assert crop.getpixel((8, 8)) == (40, 0, 0)
        assert crop.getpixel((0, 0)) == (255, 255, 255)
