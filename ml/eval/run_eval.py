"""
ml/eval/run_eval.py — Golden Evaluation Benchmark & Promotion Gate Runner.
Executes models against the sacred golden dataset (ml/data/golden), calculates the 4-tier
metrics, produces eval-rapport.md, and blocks regressions in CI/CD.
Usage:
    uv run python ml/eval/run_eval.py --model elektro-vl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from dataclasses import asdict
from math import isfinite
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import yaml

from ml.eval.detection import record_drawing
from ml.eval.metrics import (
    FullEvaluationReport,
    Level1DetectionMetrics,
    compute_level2_counting,
    compute_level3_outcome,
    Level4WorkflowMetrics,
)
from packages.pipeline import InMemoryCheckpointStore, NullMetrics, PipelineOptions, StageContext, build_default_pipeline
from packages.schema import Project

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("imjan.ml.eval")
_RASTER = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate imjan AI models on golden benchmark.")
    parser.add_argument("--model", type=str, default="pipeline", help="Label for the evaluated configuration")
    parser.add_argument("--dataset", type=str, default="ml/data/golden", help="Path to golden evaluation set")
    parser.add_argument("--config", type=str, default="ml/config/eval.yaml", help="Path to evaluation config")
    parser.add_argument("--baseline", type=str, default=None, help="Metrics JSON from a comparable benchmark")
    parser.add_argument("--report", type=str, default="eval-rapport.md", help="Output path for markdown report")
    parser.add_argument("--gate", action="store_true", default=False, help="Enforce regression gate (exit 1 if failed)")
    parser.add_argument("--metrics-json", type=Path, help="Save coordinates of each detection error")
    parser.add_argument("--detector-weights", type=Path, help="Detector checkpoint to evaluate")
    parser.add_argument("--classifier", type=Path, help="Symbol classifier checkpoint (.npz)")
    parser.add_argument("--classifier-threshold", type=float, default=0.65)
    parser.add_argument("--tiled", action="store_true", help="Run detector on overlapping tiles")
    parser.add_argument("--tile-size", type=int, default=1024)
    parser.add_argument("--tile-overlap", type=int, default=128)
    parser.add_argument("--enable-vlm", action="store_true", default=False, help="Enable VLM inference in evaluation")
    return parser.parse_args()


def load_golden_pairs(dataset_path: str | Path) -> list[tuple[bytes, Project, str]]:
    """Load drawing bytes, expected projects, and original filenames."""
    p = Path(dataset_path)
    img_dir = p / "tekeningen"
    ans_dir = p / "antwoorden"

    pairs = []
    if not (img_dir.exists() and ans_dir.exists()):
        logger.warning("Golden benchmark directories not found at %s", dataset_path)
        return []

    for ans_file in sorted(ans_dir.glob("*.json")):
        sample_id = ans_file.stem
        candidates = sorted(path for path in img_dir.glob(f"{sample_id}.*") if path.is_file())
        if len(candidates) != 1:
            raise ValueError(f"{sample_id}: expected one drawing for the reference annotation")
        drawing = candidates[0]
        gt_project = Project.model_validate_json(ans_file.read_text(encoding="utf-8"))
        pairs.append((drawing.read_bytes(), gt_project, drawing.name))

    return pairs


def run_pipeline_on_image(
    img_bytes: bytes, filename: str, vlm_enabled: bool = False, *, raster_scale: float = 1.0, detector_options: dict | None = None,
) -> Project:
    """Runs default end-to-end pipeline on an image."""
    pipeline = build_default_pipeline()
    proj = Project(name=filename)
    ctx = StageContext(
        project=proj,
        payload={"filename": filename, "source_bytes": img_bytes, "scale_hint": raster_scale},
        options=PipelineOptions(strict=False, extra={"vlm_enabled": vlm_enabled, **(detector_options or {})}),
        metrics=NullMetrics(),
    )
    store = InMemoryCheckpointStore()
    pipeline.run(ctx, store=store)
    return ctx.project


def evaluate(
    model_name: str,
    golden_pairs: list[tuple[bytes, Project, str]],
    config: dict[str, Any],
    vlm_enabled: bool = False,
    detector_options: dict | None = None,
) -> FullEvaluationReport:
    """Runs evaluation benchmark and computes all 4 tiers of metrics."""
    predictions: list[Project] = []
    ground_truths: list[Project] = []

    if not golden_pairs:
        raise ValueError("The benchmark requires annotated drawings")
    options = config.get("evaluation", {})
    raster_tolerance = float(options.get("raster_tolerance_px", 12))
    vector_tolerance = float(options.get("vector_tolerance_mm", 100))
    if any(not isfinite(value) or value <= 0 for value in (raster_tolerance, vector_tolerance)):
        raise ValueError("Benchmark tolerances must be positive and finite")

    weights = Path(os.environ.get("DETECTOR_MODEL_PATH", "models/detector.pt"))
    weights_hash = None
    if weights.is_file():
        with weights.open("rb") as stream:
            weights_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    classifier = (detector_options or {}).get("symbol_classifier")
    classifier_hash = None
    if classifier:
        with Path(classifier).open("rb") as stream:
            classifier_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    level1 = Level1DetectionMetrics()
    classifier_unavailable = []
    digest = hashlib.sha256()
    logger.info("Evaluating %d golden test drawings...", len(golden_pairs))
    for img_bytes, gt_proj, filename in golden_pairs:
        raster = Path(filename).suffix.lower() in _RASTER
        scale = gt_proj.scale if raster else 1.0
        if not isfinite(scale) or scale <= 0:
            raise ValueError(f"{filename}: invalid raster calibration")
        pred_proj = run_pipeline_on_image(
            img_bytes, filename, vlm_enabled=vlm_enabled, raster_scale=scale,
            **({"detector_options": detector_options} if detector_options is not None else {}),
        )
        predictions.append(pred_proj)
        ground_truths.append(gt_proj)
        record_drawing(
            level1, filename, pred_proj.symbols, gt_proj.symbols,
            raster_tolerance * scale if raster else vector_tolerance,
            detector=pred_proj.meta.get("detector_backend", "not_run"),
            vlm=pred_proj.meta.get("vlm_status", "not_run" if vlm_enabled else "disabled"),
        )
        drawing = level1.drawings[-1]
        drawing.classifier = pred_proj.meta.get("symbol_classifier", {"status": "not_run"})
        drawing.tile_count = pred_proj.meta.get("detector_tiles", 0)
        if raster and classifier and drawing.classifier.get("status") != "applied":
            classifier_unavailable.append(filename)
        digest.update(json.dumps([
            filename, hashlib.sha256(img_bytes).hexdigest(), scale,
            [(symbol.type.value, symbol.x, symbol.y) for symbol in gt_proj.symbols],
            [(line.symbol_type.value, line.quantity, line.total_price) for line in gt_proj.materials],
        ], ensure_ascii=False).encode())

    level2 = compute_level2_counting(predictions, ground_truths)
    level3 = compute_level3_outcome(predictions, ground_truths)
    corrections = [drawing.corrections for drawing in level1.drawings]
    level4 = Level4WorkflowMetrics(
        pct_drawings_zero_correction=100 * corrections.count(0) / len(corrections),
        avg_corrections_per_drawing=sum(corrections) / len(corrections),
    )

    gates = config.get("gates", {})
    rejections = []
    min_f1 = gates.get("min_symbol_f1", 0.85)
    if level1.overall.f1 < min_f1:
        rejections.append(f"Symbool-F1 ({level1.overall.f1:.3f}) < drempel ({min_f1:.3f})")
    if level1.overall.expected == 0:
        rejections.append("De dataset bevat geen gelabelde symbolen.")
    if weights_hash and any(
        Path(drawing.filename).suffix.lower() in _RASTER and drawing.detector != "ultralytics_yolo"
        for drawing in level1.drawings
    ):
        rejections.append("De gevraagde detectorgewichten zijn niet op alle rastertekeningen gebruikt.")

    if classifier_unavailable:
        rejections.append(f"Classifier niet uitgevoerd op: {', '.join(classifier_unavailable)}")

    max_cnt_err = gates.get("max_avg_count_error", 2.0)
    if level2.avg_total_count_error > max_cnt_err:
        rejections.append(f"Level 2: Tellingfout ({level2.avg_total_count_error:.2f}) > drempel ({max_cnt_err:.2f})")

    max_cost_pct = gates.get("max_cost_error_pct", 3.0)
    if level3.avg_cost_error_pct > max_cost_pct:
        rejections.append(f"Level 3: Kostenfout ({level3.avg_cost_error_pct:.2f}%) > drempel ({max_cost_pct:.2f}%)")

    report = FullEvaluationReport(
        model_version=model_name,
        dataset_version=digest.hexdigest(),
        level1=level1,
        level2=level2,
        level3=level3,
        level4=level4,
        promotion_eligible=len(rejections) == 0,
        rejection_reasons=rejections,
        settings={
            "Rastertolerantie (px)": raster_tolerance,
            "Vectortolerantie (mm)": vector_tolerance,
            "Detectorbestand": weights.name if weights_hash else "geen",
            "Detector SHA-256": weights_hash or "geen",
            "Classifier SHA-256": classifier_hash or "geen",
            "Classifierdrempel": (detector_options or {}).get("classifier_threshold") if classifier else "uit",
            "Tegeldetectie": bool((detector_options or {}).get("detector_tiled")),
            "Tegelgrootte": (detector_options or {}).get("tile_size", 1024),
            "Tegeloverlap": (detector_options or {}).get("tile_overlap", 128),
            "VLM aangevraagd": vlm_enabled,
            "VLM-model": os.environ.get("VLLM_MODEL", "elektro-vl") if vlm_enabled else "uit",
        },
    )
    return report


def main() -> int:
    args = parse_args()

    cfg_p = Path(args.config)
    config = {}
    if cfg_p.exists():
        with open(cfg_p, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

    try:
        if args.detector_weights:
            if not args.detector_weights.is_file():
                raise ValueError(f"Detector weights not found: {args.detector_weights}")
            os.environ["DETECTOR_MODEL_PATH"] = str(args.detector_weights.resolve())
        golden_pairs = load_golden_pairs(args.dataset)
        if not 0.5 <= args.classifier_threshold <= 1:
            raise ValueError("Classifier threshold must be between 0.5 and 1")
        if args.tile_size < 128 or not 0 <= args.tile_overlap < args.tile_size:
            raise ValueError("Tile size must be at least 128 and overlap must be smaller than the tile")
        report = evaluate(args.model, golden_pairs, config or {}, vlm_enabled=args.enable_vlm,
                          detector_options={
                              "symbol_classifier": str(args.classifier) if args.classifier else None,
                              "classifier_threshold": args.classifier_threshold,
                              "detector_tiled": args.tiled,
                              "tile_size": args.tile_size,
                              "tile_overlap": args.tile_overlap,
                          })
        if args.baseline:
            baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
            comparable = (
                baseline["dataset_version"] == report.dataset_version
                and all(baseline["settings"][key] == report.settings[key]
                        for key in ("Rastertolerantie (px)", "Vectortolerantie (mm)"))
            )
            if not comparable:
                raise ValueError("Baseline requires the same drawings, annotations and tolerances")
            old_f1 = float(baseline["symbol_f1"])
            if not 0 <= old_f1 <= 1:
                raise ValueError("Invalid baseline symbol F1")
            allowed_drop = (config or {}).get("gates", {}).get("max_symbol_f1_drop", 0.0)
            if old_f1 - report.level1.overall.f1 > allowed_drop + 1e-12:
                report.rejection_reasons.append(f"Symbool-F1 is gedaald sinds de baseline ({old_f1:.3f}).")
                report.promotion_eligible = False
    except (OSError, ValueError, KeyError) as exc:
        logger.error("Benchmark failed: %s", exc)
        return 1
    if args.metrics_json:
        metrics = {**asdict(report), "symbol_f1": report.level1.overall.f1}
        args.metrics_json.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_content = report.to_markdown()

    out_file = Path(args.report)
    out_file.write_text(md_content, encoding="utf-8")
    logger.info("Evaluation report saved to %s", out_file)
    print("\n" + md_content)

    # Log to MLflow if available
    try:
        import mlflow
        mlflow.set_experiment("golden-eval")
        with mlflow.start_run():
            mlflow.log_params({"model": args.model, "dataset": args.dataset})
            mlflow.log_metrics({
                "symbol_f1": report.level1.overall.f1,
                "symbol_precision": report.level1.overall.precision,
                "symbol_recall": report.level1.overall.recall,
                "avg_count_error": report.level2.avg_total_count_error,
                "perfect_drawings_pct": report.level2.perfect_drawings_pct,
                "cost_error_pct": report.level3.avg_cost_error_pct,
                "zero_correction_pct": report.level4.pct_drawings_zero_correction,
            })
            mlflow.log_artifact(str(out_file))
    except Exception as exc:
        logger.debug("MLflow logging skipped: %s", exc)

    if args.gate and not report.promotion_eligible:
        logger.error("Promotion gate FAILED! Model cannot be promoted.")
        return 1

    logger.info("Evaluation completed. Gate passed: %s", report.promotion_eligible)
    return 0


if __name__ == "__main__":
    sys.exit(main())
