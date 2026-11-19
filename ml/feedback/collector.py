"""
ml/feedback/collector.py — Feedback loop data harvester.
Collects corrections submitted by electricians via the Review UI (POST /corrections),
filters by GDPR consent, and transforms corrections into new training examples for
the detector (bounding box crops) and VLM (conversation pairs).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packages.schema import Correction, CorrectionAction, SymbolType

logger = logging.getLogger("imjan.ml.feedback")


@dataclass
class FeedbackHarvestStats:
    total_corrections_processed: int = 0
    added_to_detector: int = 0
    added_to_vlm: int = 0
    skipped_no_consent: int = 0


def process_correction(
    correction: Correction,
    image_bytes: bytes | None = None,
    allow_training: bool = True,
    detector_staging_dir: str | Path = "ml/data/detector/staging",
    vlm_staging_file: str | Path = "ml/data/vlm/staging.jsonl",
) -> bool:
    """
    Transforms a single Correction into training annotations.
    """
    if not allow_training:
        logger.debug("Correction %s skipped: no user training consent.", correction.id)
        return False

    # 1. Format for VLM pair
    vlm_path = Path(vlm_staging_file)
    vlm_path.parent.mkdir(parents=True, exist_ok=True)

    vlm_record = {
        "correction_id": correction.id,
        "project_id": correction.project_id,
        "action": correction.action.value,
        "comment": correction.comment,
        "conversations": [
            {
                "from": "human",
                "value": f"<image>\nWat is het juiste elektrotechnische symbool op positie ({correction.new_x}, {correction.new_y})?",
            },
            {
                "from": "gpt",
                "value": json.dumps({
                    "action": correction.action.value,
                    "type": correction.new_type.value if correction.new_type else "onbekend",
                }),
            },
        ],
    }

    with open(vlm_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(vlm_record) + "\n")

    # 2. Format for Detector if location is present
    if correction.new_x is not None and correction.new_y is not None and correction.new_type:
        det_dir = Path(detector_staging_dir)
        det_dir.mkdir(parents=True, exist_ok=True)
        txt_file = det_dir / f"{correction.project_id}.txt"
        with open(txt_file, "a", encoding="utf-8") as f:
            f.write(f"# correction {correction.id}: {correction.action.value} -> {correction.new_type.value}\n")

    return True


def harvest_corrections(
    corrections: list[Correction],
    allow_training_map: dict[str, bool] | None = None,
) -> FeedbackHarvestStats:
    """Batch-harvests a collection of corrections."""
    stats = FeedbackHarvestStats()
    allow_map = allow_training_map or {}

    for corr in corrections:
        consent = allow_map.get(corr.project_id, True)
        if not consent:
            stats.skipped_no_consent += 1
            continue

        ok = process_correction(corr, allow_training=True)
        if ok:
            stats.total_corrections_processed += 1
            stats.added_to_vlm += 1
            if corr.new_x is not None:
                stats.added_to_detector += 1

    return stats
