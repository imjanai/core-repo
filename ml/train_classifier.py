"""Train a CPU symbol classifier from verified, grouped crops."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from packages.vision.classifier import BACKGROUND, FORMAT_VERSION, features
from packages.schema import SymbolType


def train(data: Path, output: Path) -> dict[str, int]:
    vectors, labels = [], []
    size = None
    valid = {item.value for item in SymbolType if item != SymbolType.ONBEKEND} | {BACKGROUND}
    for folder in sorted((data / "train").iterdir()):
        if not folder.is_dir():
            continue
        if folder.name not in valid:
            raise ValueError(f"Unknown classifier label: {folder.name}")
        for path in sorted(folder.glob("*.png")):
            image = cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if image is None or image.shape[0] != image.shape[1]:
                raise ValueError(f"Expected a square crop: {path}")
            size = image.shape[0] if size is None else size
            if image.shape != (size, size) or not 16 <= size <= 1024 or size % 2:
                raise ValueError("Training crops must share one even size from 16 to 1024")
            vectors.append(features(image))
            labels.append(folder.name)

    counts = {label: labels.count(label) for label in sorted(set(labels))}
    if len(counts) < 2 or BACKGROUND not in counts:
        raise ValueError("Train with labelled symbols and verified background crops")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        np.savez_compressed(stream, version=FORMAT_VERSION, crop_size=size,
                            vectors=np.stack(vectors), labels=np.asarray(labels))
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(train(args.data, args.output)))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Training failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
