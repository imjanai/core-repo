"""Crop classifier shared by training and the raster analysis pipeline."""
from functools import lru_cache
from math import isfinite
from pathlib import Path

import cv2
import numpy as np

from packages.schema import SourceType, Symbol, SymbolType

BACKGROUND = "background"
FORMAT_VERSION = 1


def symbol_crop(image: np.ndarray, x: float, y: float, size: int) -> np.ndarray:
    left, top = round(x) - size // 2, round(y) - size // 2
    height, width = image.shape[:2]
    x0, y0 = max(0, left), max(0, top)
    x1, y1 = min(width, left + size), min(height, top + size)
    output = np.full((size, size, *image.shape[2:]), 255, dtype=np.uint8)
    if x1 > x0 and y1 > y0:
        output[y0 - top:y1 - top, x0 - left:x1 - left] = image[y0:y1, x0:x1]
    return output


def features(crop: np.ndarray) -> np.ndarray:
    normalized = cv2.resize(crop, (32, 32), interpolation=cv2.INTER_AREA)
    pixels = normalized.astype(np.float32) / 255
    dy, dx = np.gradient(pixels)
    bins = (np.arctan2(dy, dx) % np.pi * (9 / np.pi)).astype(np.int32).clip(0, 8)
    magnitudes = np.hypot(dx, dy)
    rows, cols = np.indices(pixels.shape)
    cells = rows // 8 * 4 + cols // 8
    histogram = np.bincount((cells * 9 + bins).ravel(), weights=magnitudes.ravel(), minlength=144)
    histogram = histogram.reshape(16, 9)
    histogram /= np.maximum(np.linalg.norm(histogram, axis=1, keepdims=True), 0.15)
    ink = (1 - pixels[::2, ::2]).reshape(-1)
    return np.concatenate((histogram.ravel(), ink * 0.5)).astype(np.float32)



@lru_cache(maxsize=2)
def _load(path: str, modified: int):
    with np.load(path, allow_pickle=False) as model:
        version, size = int(model["version"]), int(model["crop_size"])
        vectors, labels = model["vectors"], model["labels"]
    valid = {label.value for label in SymbolType} | {BACKGROUND}
    if (
        version != FORMAT_VERSION or not 16 <= size <= 1024 or size % 2
        or vectors.ndim != 2 or vectors.shape[1] != features(np.zeros((size, size), np.uint8)).size
        or labels.ndim != 1 or not len(labels) or len(labels) != len(vectors)
        or not set(labels.tolist()) <= valid or not np.isfinite(vectors).all()
    ):
        raise ValueError("Invalid symbol classifier checkpoint")
    vectors = vectors.astype(np.float32, copy=False)
    return size, vectors, labels, np.einsum("ij,ij->i", vectors, vectors)


def classify_candidates(data: bytes, symbols: list[Symbol], model_path: str, threshold: float, scale: float):
    """Retype candidates in place, leaving their position unchanged."""
    if not 0.5 <= threshold <= 1:
        raise ValueError("Classifier confidence threshold must be between 0.5 and 1")
    if not isfinite(scale) or scale <= 0:
        raise ValueError("Classifier requires a positive raster scale")
    path = Path(model_path).resolve()
    size, training, labels, training_norms = _load(str(path), path.stat().st_mtime_ns)
    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("Classifier expected raster image bytes")
    candidates = [symbol for symbol in symbols if symbol.source == SourceType.DETECTOR]
    rejected = set()
    unknown = 0
    neighbours = min(len(labels), 5)
    for start in range(0, len(candidates), 64):
        batch = candidates[start:start + 64]
        queries = np.stack([
            features(symbol_crop(image, symbol.x / scale, symbol.y / scale, size))
            for symbol in batch
        ])
        distances = np.maximum(
            np.einsum("ij,ij->i", queries, queries)[:, None] + training_norms
            - 2 * queries @ training.T, 0,
        )
        for symbol, row in zip(batch, distances):
            positions = np.argsort(row, kind="stable")[:neighbours]
            vote = {}
            for index in positions:
                label = str(labels[index])
                vote[label] = vote.get(label, 0.0) + 1 / (0.05 + float(row[index]))
            label = max(vote, key=vote.get)
            score = vote[label] / sum(vote.values())
            symbol.attributes["classifier"] = {
                "previous_type": symbol.type.value, "previous_confidence": symbol.confidence,
                "label": label, "vote_share": round(score, 4),
            }
            symbol.confidence = round(score, 3)
            if score < threshold:
                symbol.type = SymbolType.ONBEKEND
                unknown += 1
            elif label == BACKGROUND:
                rejected.add(symbol.id)
            else:
                symbol.type = SymbolType(label)
    return [symbol for symbol in symbols if symbol.id not in rejected], {
        "candidates": len(candidates), "background": len(rejected), "unknown": unknown,
    }
