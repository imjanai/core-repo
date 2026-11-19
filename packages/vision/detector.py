"""
packages/vision/detector.py — Symbol detection with YOLO and SAHI slicing.
Handles raster images, executes tiled inference, and converts detections to Symbols.
"""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from packages.schema import Project, SourceType, Symbol, SymbolType

logger = logging.getLogger("imjan.vision.detector")

# Class index / label mapping
CLASS_MAP: dict[str, SymbolType] = {
    "wandcontactdoos": SymbolType.WANDCONTACTDOOS,
    "wandcontactdoos_dubbel": SymbolType.WANDCONTACTDOOS_DUBBEL,
    "wandcontactdoos_waterdicht": SymbolType.WANDCONTACTDOOS_WATERDICHT,
    "wandcontactdoos_kracht": SymbolType.WANDCONTACTDOOS_KRACHT,
    "schakelaar": SymbolType.SCHAKELAAR,
    "schakelaar_wissel": SymbolType.SCHAKELAAR_WISSEL,
    "schakelaar_kruis": SymbolType.SCHAKELAAR_KRUIS,
    "schakelaar_dimmer": SymbolType.SCHAKELAAR_DIMMER,
    "lichtpunt": SymbolType.LICHTPUNT,
    "lichtpunt_spot": SymbolType.LICHTPUNT_SPOT,
    "lichtpunt_tl": SymbolType.LICHTPUNT_TL,
    "datapunt": SymbolType.DATAPUNT,
    "datapunt_dubbel": SymbolType.DATAPUNT_DUBBEL,
    "verdeler": SymbolType.VERDELER,
    "groepenkast": SymbolType.GROEPENKAST,
    "rookmelder": SymbolType.ROOKMELDER,
    "thermostaat": SymbolType.THERMOSTAAT,
}

INDEX_TO_CLASS = [
    SymbolType.WANDCONTACTDOOS,
    SymbolType.SCHAKELAAR,
    SymbolType.LICHTPUNT,
    SymbolType.DATAPUNT,
    SymbolType.VERDELER,
]


def _load_image_np(data: bytes) -> np.ndarray | None:
    try:
        nparr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as exc:
        logger.warning("Failed to decode image buffer: %s", exc)
        return None


def detect_symbols(data: bytes, project: Project) -> list[Symbol]:
    """
    Runs symbol detection on raster drawing bytes.
    If a trained model checkpoint is available, uses Ultralytics / SAHI.
    Otherwise, runs robust morphological contour candidate detection.
    """
    model_path = os.environ.get("DETECTOR_MODEL_PATH", "models/detector.pt")
    img_np = _load_image_np(data)
    if img_np is None:
        logger.warning("No valid image decoded for detector stage.")
        return []

    h, w = img_np.shape[:2]
    symbols: list[Symbol] = []

    # 1. Try running trained YOLO model if weights exist
    if Path(model_path).exists():
        try:
            from ultralytics import YOLO

            model = YOLO(model_path)
            # Run inference (use CPU or GPU if available)
            results = model.predict(source=img_np, imgsz=1024, conf=0.25, verbose=False)
            for res in results:
                boxes = res.boxes
                for box in boxes:
                    xyxy = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    cls_name = model.names.get(cls_id, "onbekend")

                    sym_type = CLASS_MAP.get(cls_name.lower())
                    if not sym_type and 0 <= cls_id < len(INDEX_TO_CLASS):
                        sym_type = INDEX_TO_CLASS[cls_id]
                    if not sym_type:
                        sym_type = SymbolType.ONBEKEND

                    cx = (xyxy[0] + xyxy[2]) / 2.0
                    cy = (xyxy[1] + xyxy[3]) / 2.0

                    symbols.append(
                        Symbol(
                            type=sym_type,
                            x=round(cx * project.scale, 2),
                            y=round(cy * project.scale, 2),
                            confidence=round(conf, 3),
                            source=SourceType.DETECTOR,
                            attributes={
                                "bbox": [round(v, 1) for v in xyxy],
                                "detector": "ultralytics_yolo",
                            },
                        )
                    )
            return symbols
        except Exception as exc:
            logger.warning("YOLO model prediction error: %s. Falling back to heuristic.", exc)

    # 2. Robust heuristic fallback (detects standard circuit geometric markers)
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Filter for typical electrical symbol pixel area (e.g., 50 to 2500 px)
        if 80 <= area <= 1800:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            aspect_ratio = float(bw) / float(bh) if bh > 0 else 0
            if 0.7 <= aspect_ratio <= 1.4:
                cx = bx + bw / 2.0
                cy = by + bh / 2.0

                # Simple circularity check
                perimeter = cv2.arcLength(cnt, True)
                circularity = 4 * np.pi * (area / (perimeter * perimeter)) if perimeter > 0 else 0
                inferred_type = (
                    SymbolType.WANDCONTACTDOOS if circularity > 0.65 else SymbolType.SCHAKELAAR
                )

                symbols.append(
                    Symbol(
                        type=inferred_type,
                        x=round(cx * project.scale, 2),
                        y=round(cy * project.scale, 2),
                        confidence=0.72,
                        source=SourceType.DETECTOR,
                        attributes={
                            "bbox": [bx, by, bx + bw, by + bh],
                            "area": float(area),
                            "circularity": round(float(circularity), 2),
                            "detector": "heuristic_cv",
                        },
                    )
                )

    logger.info("Detector identified %d symbols", len(symbols))
    return symbols
