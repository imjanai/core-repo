"""
tests/vision/test_detector.py — Unit tests for the vision detector.
"""

import cv2
import numpy as np
import pytest

from packages.schema import Project, SourceType, SymbolType
from packages.vision.detector import detect_symbols


def test_detect_symbols_synthetic_image():
    # Create white canvas with a black circular symbol
    img = np.ones((500, 500, 3), dtype=np.uint8) * 255
    cv2.circle(img, (250, 250), 12, (0, 0, 0), 2)
    cv2.line(img, (238, 250), (262, 250), (0, 0, 0), 2)

    _, png_bytes = cv2.imencode(".png", img)
    proj = Project(scale=1.0)
    symbols = detect_symbols(png_bytes.tobytes(), proj)

    assert isinstance(symbols, list)
    assert len(symbols) >= 1
    assert symbols[0].source == SourceType.DETECTOR


def test_detect_symbols_empty_bytes():
    proj = Project()
    res = detect_symbols(b"", proj)
    assert res == []

def test_tiled_detector_restores_coordinates_and_deduplicates_overlap(monkeypatch):
    import packages.vision.detector as detector

    monkeypatch.setenv("DETECTOR_MODEL_PATH", "nonexistent.pt")
    image = np.full((128, 216, 3), 255, dtype=np.uint8)
    cv2.circle(image, (104, 74), 10, (0, 0, 0), -1)
    cv2.circle(image, (167, 49), 10, (0, 0, 0), -1)
    data = cv2.imencode(".png", image)[1].tobytes()
    project = Project(scale=2)
    symbols = detector.detect_symbols(data, project, tiles=[
        {"x": 0, "y": 0, "w": 128, "h": 128},
        {"x": 88, "y": 0, "w": 128, "h": 128},
    ])

    assert len(symbols) == 2
    assert sorted((symbol.x, symbol.y) for symbol in symbols) == [(209, 149), (335, 99)]
    assert project.meta["detector_tiles"] == 2
