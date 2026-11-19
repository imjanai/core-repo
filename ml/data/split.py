"""
ml/data/split.py — Deterministic project-based dataset splitter.
Enforces the holy rule: splitting happens per drawing/project, never per tile or symbol.
Guarantees zero data leakage between train, val, and golden evaluation sets.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

import yaml


def hash_project_split(
    project_id: str,
    train_ratio: float = 0.8,
    val_ratio: float = 0.2,
    salt: str = "imjan-split-v1",
) -> Literal["train", "val"]:
    """
    Deterministically maps a project_id to 'train' or 'val' using SHA-256 hashing.
    """
    key = f"{salt}:{project_id}".encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()
    ratio = int(digest[:8], 16) / 0xFFFFFFFF
    if ratio < train_ratio:
        return "train"
    return "val"


def create_or_update_splits(
    project_ids: list[str],
    golden_ids: list[str],
    output_path: str | Path = "ml/data/splitsing.yaml",
) -> dict[str, list[str]]:
    """
    Generates splitsing.yaml mapping project IDs to 'golden', 'train', and 'val'.
    Ensures that golden IDs are strictly isolated and never included in train or val.
    """
    golden_set = set(golden_ids)
    train_list: list[str] = []
    val_list: list[str] = []

    for pid in sorted(set(project_ids)):
        if pid in golden_set:
            continue
        split = hash_project_split(pid)
        if split == "train":
            train_list.append(pid)
        else:
            val_list.append(pid)

    splits = {
        "golden": sorted(golden_set),
        "train": train_list,
        "val": val_list,
        "metadata": {
            "total_golden": len(golden_set),
            "total_train": len(train_list),
            "total_val": len(val_list),
            "salt": "imjan-split-v1",
        },
    }

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(splits, f, sort_keys=False)

    return splits
