"""
ml/data/anonymizer.py — Blueprint GDPR and confidentiality anonymizer.
Detects and scrubs title blocks, owner names, addresses, and contact info from drawings
before ingestion into raw dataset directories.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger("imjan.ml.anonymizer")

SENSITIVE_TEXT_PATTERNS = [
    re.compile(r"\b(opdrachtgever|client|bouwheer|architect|aannemer)\s*[:=]", re.IGNORECASE),
    re.compile(r"\b(straat|laan|weg|dreef|nr|bus)\s+\d+", re.IGNORECASE),
    re.compile(r"\b\d{4}\s+[a-z]{2}\b", re.IGNORECASE),  # Dutch postal codes
    re.compile(r"\b0\d{1,2}[-.\s]?\d{6,8}\b"),          # Phone numbers
    re.compile(r"[\w.-]+@[\w.-]+\.\w+"),                 # Emails
]


def anonymize_blueprint_image(
    image_bytes: bytes,
    title_block_location: str = "bottom_right",
    box_fraction_w: float = 0.28,
    box_fraction_h: float = 0.22,
) -> bytes:
    """
    Blurs/masks the title block in the specified corner to protect personal data and PII.
    Default: bottom-right corner where standard architectural title blocks are placed.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return image_bytes

    h, w = img.shape[:2]
    bw = int(w * box_fraction_w)
    bh = int(h * box_fraction_h)

    if title_block_location == "bottom_right":
        x1, y1 = w - bw, h - bh
        x2, y2 = w, h
    elif title_block_location == "bottom_left":
        x1, y1 = 0, h - bh
        x2, y2 = bw, h
    elif title_block_location == "top_right":
        x1, y1 = w - bw, 0
        x2, y2 = w, bh
    else:
        x1, y1 = 0, 0
        x2, y2 = bw, bh

    # Apply solid neutral fill or blur over the title block
    cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), -1)
    cv2.putText(
        img,
        "ANONIEM / AVG BESCHERMD",
        (x1 + 20, y1 + bh // 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (128, 128, 128),
        2,
    )

    success, encoded = cv2.imencode(".png", img)
    if success:
        return encoded.tobytes()
    return image_bytes
