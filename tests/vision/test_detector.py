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
