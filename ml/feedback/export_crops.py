"""Export verified raster symbol crops for classification or VLM fine-tuning."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from math import isfinite
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

from ml.data.split import hash_project_split
from packages.schema import Project, SymbolType
from packages.vision.classifier import BACKGROUND, symbol_crop


class ReviewedDrawing(BaseModel):
    drawing: Path
    reviewed: Path
    project_family: str = Field(min_length=1)
    allow_training: bool = False
    background_px: list[tuple[float, float]] = Field(default_factory=list)


class CropManifest(BaseModel):
    drawings: list[ReviewedDrawing]
    golden_families: set[str]


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def export_crops(manifest_path: Path, output: Path, crop_size: int = 96) -> dict[str, int]:
    if crop_size < 16 or crop_size > 1024 or crop_size % 2:
        raise ValueError("crop size must be an even integer from 16 to 1024")
    if output.exists():
        raise ValueError(f"Output directory already exists: {output}")
    manifest = CropManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    entries = {}
    for item in manifest.drawings:
        digest = _sha256(manifest_path.parent / item.drawing)
        previous = entries.get(digest)
        if previous:
            if previous.project_family != item.project_family:
                raise ValueError("An identical drawing appears in different project families")
            raise ValueError(f"Duplicate drawing: {item.drawing}")
        entries[digest] = item

    counts = Counter({"train": 0, "val": 0, "withheld": 0, "unknown": 0})
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".crops-", dir=output.parent) as temporary:
        staging = Path(temporary) / "dataset"
        staging.mkdir()
        for digest, item in entries.items():
            if not item.allow_training or item.project_family in manifest.golden_families:
                counts["withheld"] += 1
                continue
            split = hash_project_split(item.project_family)
            project = Project.model_validate_json(
                (manifest_path.parent / item.reviewed).read_text(encoding="utf-8"),
            )
            if project.file_type.value != "image" or not isfinite(project.scale) or project.scale <= 0:
                raise ValueError(f"{item.reviewed}: expected raster Project annotations with a positive scale")
            with Image.open(manifest_path.parent / item.drawing) as source:
                image = np.asarray(source.convert("RGB"))
            height, width = image.shape[:2]
            samples = []
            positions = [(symbol.x / project.scale, symbol.y / project.scale) for symbol in project.symbols]
            for symbol, (px, py) in zip(project.symbols, positions):
                if symbol.type == SymbolType.ONBEKEND:
                    counts["unknown"] += 1
                else:
                    samples.append((symbol.type.value, px, py))
            for px, py in item.background_px:
                if any(abs(px - x) <= crop_size / 2 and abs(py - y) <= crop_size / 2 for x, y in positions):
                    raise ValueError(f"{item.drawing}: background crop contains an annotated symbol center")
                samples.append((BACKGROUND, px, py))
            with (staging / f"{split}.jsonl").open("a", encoding="utf-8") as stream:
                for index, (label, px, py) in enumerate(samples):
                    if not (0 <= px < width and 0 <= py < height):
                        raise ValueError(f"{item.drawing}: crop {index + 1} lies outside the raster")
                    crop = symbol_crop(image, px, py, crop_size)
                    relative = Path(split, label, f"{digest}-{index}.png")
                    target = staging / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    Image.fromarray(crop).save(target)
                    record = {
                        "image": (output.resolve() / relative).as_posix(),
                        "project_family": item.project_family,
                        "label": label,
                        "conversations": [
                            {"from": "human", "value": "<image> Welk elektrotechnisch symbool staat in het midden?"},
                            {"from": "gpt", "value": label},
                        ],
                    }
                    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                    counts[split] += 1
        if not (counts["train"] or counts["val"]):
            raise ValueError("No eligible, verified symbol crops to export")
        staging.rename(output)
    return dict(counts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--crop-size", type=int, default=96)
    args = parser.parse_args()
    try:
        counts = export_crops(args.manifest, args.output, args.crop_size)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Crop export failed: {exc}\n")
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
