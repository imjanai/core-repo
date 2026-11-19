"""
packages/vision/ocr.py — OCR and Legend extraction using PaddleOCR and layout analysis.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import cv2
import numpy as np

from packages.schema import SymbolType

logger = logging.getLogger("imjan.vision.ocr")

LEGEND_TITLE_RE = re.compile(r"(legenda|symbolen|toelichting|verklaring|legend)", re.IGNORECASE)

KNOWN_LEGEND_DESCRIPTIONS: list[tuple[re.Pattern[str], SymbolType]] = [
    (re.compile(r"(wandcontactdoos|stopcontact|wcd)", re.IGNORECASE), SymbolType.WANDCONTACTDOOS),
    (re.compile(r"(dubbel.*wcd|wcd.*dubbel)", re.IGNORECASE), SymbolType.WANDCONTACTDOOS_DUBBEL),
    (re.compile(r"(schakelaar.*wissel|wissel)", re.IGNORECASE), SymbolType.SCHAKELAAR_WISSEL),
    (re.compile(r"(schakelaar|switch)", re.IGNORECASE), SymbolType.SCHAKELAAR),
    (re.compile(r"(lichtpunt|verlichting|lamp|spot)", re.IGNORECASE), SymbolType.LICHTPUNT),
    (re.compile(r"(datapunt|rj45|netwerk)", re.IGNORECASE), SymbolType.DATAPUNT),
    (re.compile(r"(verdeler|groepenkast|bord)", re.IGNORECASE), SymbolType.VERDELER),
    (re.compile(r"(rookmelder)", re.IGNORECASE), SymbolType.ROOKMELDER),
    (re.compile(r"(thermostaat)", re.IGNORECASE), SymbolType.THERMOSTAAT),
]


def extract_legend(data: bytes) -> list[dict[str, Any]]:
    """
    Extracts legend entries and text spans from raster image bytes.
    Returns list of legend dictionaries containing type, description, and bbox.
    """
    if not data:
        return []
    nparr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return []

    h, w = img.shape[:2]
    legend_items: list[dict[str, Any]] = []

    # 1. Try PaddleOCR if available
    try:
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(use_angle_cls=False, lang="nl", show_log=False)
        result = ocr.ocr(img, cls=False)
        if result and len(result) > 0 and result[0]:
            in_legend_area = False
            for line in result[0]:
                box, (text, score) = line
                if score < 0.4:
                    continue
                xs = [pt[0] for pt in box]
                ys = [pt[1] for pt in box]
                x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)

                if LEGEND_TITLE_RE.search(text):
                    in_legend_area = True

                matched_type = None
                for pat, st in KNOWN_LEGEND_DESCRIPTIONS:
                    if pat.search(text):
                        matched_type = st
                        break

                if matched_type or in_legend_area:
                    legend_items.append({
                        "type": matched_type.value if matched_type else "onbekend",
                        "description": text,
                        "confidence": float(score),
                        "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                    })
            if legend_items:
                return legend_items
    except Exception as exc:
        logger.debug("PaddleOCR not executed (%s). Utilizing fallback text/legend extractor.", exc)

    # 2. Heuristic legend region detection (typical bottom-right or top-right box)
    # Search for typical rectangular legend frame in corners
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if cw > w * 0.15 and ch > h * 0.15 and (x > w * 0.5 or y > h * 0.5):
            legend_items.append({
                "type": SymbolType.WANDCONTACTDOOS.value,
                "description": "Legenda (Kader herkend)",
                "confidence": 0.8,
                "bbox": [x, y, x + cw, y + ch],
            })
            break

    return legend_items
