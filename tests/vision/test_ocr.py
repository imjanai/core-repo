"""
tests/vision/test_ocr.py — Unit tests for the OCR and legend extractor.
"""

import cv2
import numpy as np
import pytest

from packages.vision.ocr import extract_legend


def test_extract_legend_synthetic():
    img = np.ones((800, 800, 3), dtype=np.uint8) * 255
    # Draw a legend box in bottom right
    cv2.rectangle(img, (500, 500), (780, 780), (0, 0, 0), 2)
    cv2.putText(img, "LEGENDA", (520, 540), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    _, png_bytes = cv2.imencode(".png", img)
    items = extract_legend(png_bytes.tobytes())
    assert isinstance(items, list)
    assert len(items) >= 1


def test_extract_legend_invalid():
    items = extract_legend(b"")
    assert items == []
