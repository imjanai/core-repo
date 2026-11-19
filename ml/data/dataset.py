"""
ml/data/dataset.py — Dataset integrity validator and loader.
Verifies format adherence for YOLO detector labels and VLM JSONL conversations.
Strictly checks that the golden evaluation set is never touched during training.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("imjan.ml.dataset")


class DataLeakageError(Exception):
    """Raised when evaluation golden samples are found in the training or validation sets."""


class DatasetValidationError(Exception):
    """Raised when annotations fail format, coordinate, or type checks."""


def check_leakage(split_file: str | Path = "ml/data/splitsing.yaml") -> None:
    """
    Checks splitsing.yaml to ensure golden project IDs never overlap with train or val.
    """
    p = Path(split_file)
    if not p.exists():
        logger.warning("No %s found. Skipping split validation check.", split_file)
        return

    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    golden = set(data.get("golden", []))
    train = set(data.get("train", []))
    val = set(data.get("val", []))

    leak_train = golden.intersection(train)
    if leak_train:
        raise DataLeakageError(
            f"CRITICAL: Golden evaluation samples leaked into train split: {leak_train}"
        )

    leak_val = golden.intersection(val)
    if leak_val:
        raise DataLeakageError(
            f"CRITICAL: Golden evaluation samples leaked into val split: {leak_val}"
        )

    overlap = train.intersection(val)
    if overlap:
        raise DataLeakageError(f"Overlap detected between train and val splits: {overlap}")

    logger.info("Dataset leakage check passed: %d golden, %d train, %d val.", len(golden), len(train), len(val))


def validate_yolo_labels(labels_dir: str | Path, num_classes: int = 5) -> dict[str, int]:
    """
    Validates YOLO formatted label files:
    Format per line: <class_id> <x_center> <y_center> <width> <height>
    Checks that coordinates are normalized between 0.0 and 1.0 and class_id is valid.
    """
    dir_path = Path(labels_dir)
    if not dir_path.exists():
        return {"total_files": 0, "total_boxes": 0}

    total_files = 0
    total_boxes = 0
    for txt_file in dir_path.glob("*.txt"):
        total_files += 1
        with open(txt_file, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                parts = line.strip().split()
                if not parts:
                    continue
                if len(parts) != 5:
                    raise DatasetValidationError(
                        f"{txt_file}:{line_no} invalid YOLO format (expected 5 tokens, got {len(parts)})"
                    )
                cls_id = int(parts[0])
                if not (0 <= cls_id < num_classes):
                    raise DatasetValidationError(
                        f"{txt_file}:{line_no} class_id {cls_id} out of bounds [0, {num_classes-1}]"
                    )
                coords = [float(p) for p in parts[1:]]
                for c in coords:
                    if not (0.0 <= c <= 1.0):
                        raise DatasetValidationError(
                            f"{txt_file}:{line_no} normalized coordinate {c} not in [0.0, 1.0]"
                        )
                total_boxes += 1

    return {"total_files": total_files, "total_boxes": total_boxes}


def validate_vlm_jsonl(jsonl_file: str | Path) -> dict[str, int]:
    """
    Validates VLM JSONL conversations format.
    Expects: {"image": str, "conversations": [{"from": "human", "value": "..."}, {"from": "gpt", "value": "..."}]}
    """
    p = Path(jsonl_file)
    if not p.exists():
        return {"total_examples": 0}

    count = 0
    with open(p, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetValidationError(f"{p}:{idx} invalid JSON: {exc}")

            if "conversations" not in record:
                raise DatasetValidationError(f"{p}:{idx} missing 'conversations' key")

            convs = record["conversations"]
            if not isinstance(convs, list) or len(convs) < 2:
                raise DatasetValidationError(f"{p}:{idx} 'conversations' must contain at least prompt and answer")
            count += 1

    return {"total_examples": count}
