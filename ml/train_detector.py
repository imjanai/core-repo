"""
ml/train_detector.py — Production training pipeline for Ultralytics YOLO / RT-DETR symbol detector.
Includes dataset integrity checks, MLflow tracking, multi-device support, ONNX export, and regression gates.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

from ml.data.dataset import check_leakage, validate_yolo_labels

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("imjan.ml.train_detector")


def create_dataset_yaml(config: dict[str, Any], output_path: str = "ml/data/detector/data.yaml") -> str:
    """Generates the Ultralytics data.yaml descriptor."""
    base_path = Path(config["data"]["dataset_path"]).resolve()
    classes = config["model"]["classes"]

    data_dict = {
        "path": str(base_path).replace("\\", "/"),
        "train": config["data"]["train"],
        "val": config["data"]["val"],
        "names": {int(k): v for k, v in classes.items()},
    }

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        yaml.safe_dump(data_dict, f, sort_keys=False)

    return str(out_p)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train imjan AI symbol detector.")
    parser.add_argument("--config", type=str, default="ml/config/detector.yaml", help="Path to config yaml")
    parser.add_argument("--epochs", type=int, default=None, help="Override number of training epochs")
    parser.add_argument("--batch", type=int, default=None, help="Override batch size")
    parser.add_argument("--imgsz", type=int, default=None, help="Override image size")
    parser.add_argument("--device", type=str, default=None, help="Device to use: 'cuda', 'cpu', '0', etc.")
    parser.add_argument("--baseline-map", type=float, default=None, help="Baseline mAP@50 to check against for regression")
    parser.add_argument("--export-onnx", action="store_true", help="Export best model to ONNX after training")
    parser.add_argument("--dry-run", action="store_true", help="Validate data and setup without running full training")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # 1. Load configuration
    cfg_path = Path(args.config)
    if not cfg_path.exists():
        logger.error("Configuration file not found: %s", cfg_path)
        return 1

    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 2. Enforce the Holy Rule: Verify zero leakage of golden evaluation set
    logger.info("Executing dataset leakage check...")
    try:
        check_leakage("ml/data/splitsing.yaml")
    except Exception as exc:
        logger.critical("Data leakage verification FAILED: %s", exc)
        return 2

    # 3. Validate training labels
    labels_train_dir = Path(config["data"]["dataset_path"]) / "labels" / "train"
    train_stats = validate_yolo_labels(labels_train_dir, num_classes=config["model"]["num_classes"])
    logger.info("Dataset verified: %d files, %d bounding boxes in train split.",
                train_stats["total_files"], train_stats["total_boxes"])

    if train_stats["total_boxes"] == 0:
        logger.warning("No training annotations found in %s.", labels_train_dir)
        if not args.dry_run:
            return 1

    # 4. Create data.yaml descriptor
    data_yaml_path = create_dataset_yaml(config)
    logger.info("Generated Ultralytics dataset descriptor at %s", data_yaml_path)

    if args.dry_run:
        logger.info("Dry run succeeded. Dataset and configuration are valid.")
        return 0

    # 5. Device detection
    import torch
    device = args.device or config["training"].get("device", "auto")
    if device == "auto":
        device = "0" if torch.cuda.is_available() else "cpu"
    logger.info("Selected training device: %s (CUDA available: %s)", device, torch.cuda.is_available())

    # 6. MLflow Tracking Setup
    use_mlflow = config["tracking"].get("tracker") == "mlflow"
    if use_mlflow:
        try:
            import mlflow
            mlflow.set_experiment(config["tracking"].get("experiment_name", "detector-training"))
            mlflow.start_run()
            mlflow.log_params({
                "architecture": config["model"]["architecture"],
                "imgsz": args.imgsz or config["data"]["imgsz"],
                "batch_size": args.batch or config["training"]["batch_size"],
                "epochs": args.epochs or config["training"]["epochs"],
                "seed": config["training"]["seed"],
                "device": device,
            })
            logger.info("MLflow run started.")
        except Exception as exc:
            logger.warning("MLflow initialization skipped: %s", exc)
            use_mlflow = False

    # 7. Initialize and Train Model
    from ultralytics import YOLO

    model_arch = config["model"]["architecture"]
    logger.info("Initializing YOLO model: %s", model_arch)
    model = YOLO(model_arch)

    epochs = args.epochs if args.epochs is not None else config["training"]["epochs"]
    batch = args.batch if args.batch is not None else config["training"]["batch_size"]
    imgsz = args.imgsz if args.imgsz is not None else config["data"]["imgsz"]

    logger.info("Starting training: epochs=%d, batch=%d, imgsz=%d, device=%s", epochs, batch, imgsz, device)

    train_results = model.train(
        data=data_yaml_path,
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        device=device,
        seed=config["training"]["seed"],
        optimizer=config["training"]["optimizer"],
        lr0=config["training"]["learning_rate"],
        patience=config["training"]["patience"],
        project="runs/detector",
        name="imjan_detector",
        exist_ok=True,
        verbose=True,
    )

    # 8. Validation and Metrics Extraction
    logger.info("Evaluating model on validation split...")
    val_results = model.val(data=data_yaml_path, imgsz=imgsz, device=device)

    map50 = float(getattr(val_results.box, "map50", 0.0))
    map50_95 = float(getattr(val_results.box, "map", 0.0))
    precision = float(getattr(val_results.box, "mp", 0.0))
    recall = float(getattr(val_results.box, "mr", 0.0))

    logger.info("Validation Results — mAP@50: %.4f | mAP@50-95: %.4f | P: %.4f | R: %.4f",
                map50, map50_95, precision, recall)

    if use_mlflow:
        try:
            import mlflow
            mlflow.log_metrics({
                "val_map50": map50,
                "val_map50_95": map50_95,
                "val_precision": precision,
                "val_recall": recall,
            })
        except Exception:
            pass

    # 9. Regression Gate Check
    baseline_map = args.baseline_map or config["tracking"].get("min_map50_threshold", 0.0)
    if baseline_map > 0.0 and map50 < baseline_map:
        msg = f"REGRESSION DETECTED: mAP@50 ({map50:.4f}) is below required baseline ({baseline_map:.4f}). Promotion blocked!"
        logger.error(msg)
        if use_mlflow:
            import mlflow
            mlflow.end_run(status="FAILED")
        return 3

    # 10. Model Export (ONNX)
    if args.export_onnx or config["tracking"].get("export_onnx", False):
        try:
            logger.info("Exporting best weights to ONNX format...")
            exported_path = model.export(format="onnx", imgsz=imgsz)
            logger.info("Model exported successfully: %s", exported_path)
            if use_mlflow:
                import mlflow
                mlflow.log_artifact(str(exported_path))
        except Exception as exc:
            logger.warning("ONNX export failed: %s", exc)

    # Save to production models directory
    dest_weights = Path("models/detector.pt")
    dest_weights.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(train_results, "save_dir"):
        best_pt = Path(train_results.save_dir) / "weights" / "best.pt"
        if best_pt.exists():
            import shutil
            shutil.copy(best_pt, dest_weights)
            logger.info("Saved production detector checkpoint to %s", dest_weights)

    if use_mlflow:
        import mlflow
        mlflow.end_run(status="FINISHED")

    logger.info("Training pipeline completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
