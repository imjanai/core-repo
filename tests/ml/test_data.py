"""
tests/ml/test_data.py — Unit tests for ML dataset processing, anonymization, and leakage check.
"""

import json
from pathlib import Path
import pytest
import yaml

from ml.data.anonymizer import anonymize_blueprint_image
from ml.data.converters import coco_to_yolo, label_studio_to_yolo
from ml.data.dataset import DataLeakageError, check_leakage, validate_vlm_jsonl, validate_yolo_labels
from ml.data.split import create_or_update_splits, hash_project_split
from ml.feedback.collector import process_correction
from packages.schema import Correction, CorrectionAction, SymbolType


def test_split_and_leakage_detection(tmp_path: Path):
    split_file = tmp_path / "splitsing.yaml"
    golden = ["proj-gold-1", "proj-gold-2"]
    others = ["proj-a", "proj-b", "proj-c", "proj-d"]

    splits = create_or_update_splits(others, golden, split_file)
    assert len(splits["golden"]) == 2
    assert "proj-gold-1" in splits["golden"]
    assert "proj-gold-1" not in splits["train"]
    assert "proj-gold-1" not in splits["val"]

    # Passing check
    check_leakage(split_file)

    # Intentionally corrupt split to verify leak detection
    corrupt_splits = {
        "golden": ["proj-gold-1"],
        "train": ["proj-gold-1", "proj-a"],
        "val": ["proj-b"],
    }
    with open(split_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(corrupt_splits, f)

    with pytest.raises(DataLeakageError):
        check_leakage(split_file)


def test_coco_to_yolo_conversion(tmp_path: Path):
    coco_data = {
        "images": [{"id": 1, "file_name": "plan_01.png", "width": 1000, "height": 1000}],
        "categories": [{"id": 10, "name": "wandcontactdoos"}],
        "annotations": [
            {"id": 101, "image_id": 1, "category_id": 10, "bbox": [100, 200, 50, 50]}
        ],
    }
    coco_file = tmp_path / "coco.json"
    coco_file.write_text(json.dumps(coco_data), encoding="utf-8")

    labels_out = tmp_path / "labels"
    num_converted = coco_to_yolo(coco_file, labels_out)
    assert num_converted == 1

    txt_file = labels_out / "plan_01.txt"
    assert txt_file.exists()
    content = txt_file.read_text().strip()
    parts = content.split()
    assert parts[0] == "0"  # class 0 for wandcontactdoos


def test_blueprint_anonymization():
    import cv2
    import numpy as np

    img = np.ones((400, 400, 3), dtype=np.uint8) * 200
    _, png = cv2.imencode(".png", img)
    anonymized = anonymize_blueprint_image(png.tobytes())
    assert isinstance(anonymized, bytes)
    assert len(anonymized) > 0


def test_feedback_correction_processing(tmp_path: Path):
    staging_file = tmp_path / "staging.jsonl"
    staging_dir = tmp_path / "det_staging"

    corr = Correction(
        project_id="test-p1",
        action=CorrectionAction.ADD,
        new_type=SymbolType.WANDCONTACTDOOS,
        new_x=1200.0,
        new_y=1500.0,
        comment="Gemist door detector",
    )
    ok = process_correction(
        corr,
        allow_training=True,
        detector_staging_dir=staging_dir,
        vlm_staging_file=staging_file,
    )
    assert ok is True
    assert staging_file.exists()
    lines = staging_file.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["action"] == "add"
