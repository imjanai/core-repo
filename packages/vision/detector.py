"""
packages/vision/detector.py — Symbol detection with YOLO and SAHI slicing.
Handles raster images, executes tiled inference, and converts detections to Symbols.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import cv2
import numpy as np

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


def _heuristic(image):
    symbols = []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
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
                        x=cx,
                        y=cy,
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

    return symbols


def _yolo_symbols(model, image):
    symbols = []
    for result in model.predict(source=image, imgsz=1024, conf=0.25, verbose=False):
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            class_id = int(box.cls[0])
            names = model.names
            class_name = names.get(class_id, "") if isinstance(names, dict) else (
                names[class_id] if 0 <= class_id < len(names) else ""
            )
            fallback = INDEX_TO_CLASS[class_id] if 0 <= class_id < len(INDEX_TO_CLASS) else SymbolType.ONBEKEND
            symbols.append(Symbol(
                type=CLASS_MAP.get(class_name.lower(), fallback),
                x=(x1 + x2) / 2, y=(y1 + y2) / 2,
                confidence=round(float(box.conf[0]), 3), source=SourceType.DETECTOR,
                attributes={"bbox": [x1, y1, x2, y2], "detector": "ultralytics_yolo"},
            ))
    return symbols


def _predict_regions(image, predict, tiles):
    if len(tiles) <= 1:
        return predict(image)
    height, width = image.shape[:2]
    symbols = []
    boxes = []
    for tile in tiles:
        x, y, w, h = (tile[key] for key in ("x", "y", "w", "h"))
        for symbol in predict(image[y:y+h, x:x+w]):
            x1, y1, x2, y2 = symbol.attributes["bbox"]
            if ((x > 0 and x1 <= 1) or (y > 0 and y1 <= 1)
                or (x + w < width and x2 >= w - 1) or (y + h < height and y2 >= h - 1)):
                continue
            symbol.x += x
            symbol.y += y
            symbol.attributes["bbox"] = [x1 + x, y1 + y, x2 + x, y2 + y]
            boxes.append([x1 + x, y1 + y, x2 - x1, y2 - y1])
            symbols.append(symbol)
    if not symbols:
        return []
    indices = cv2.dnn.NMSBoxes(boxes, [symbol.confidence for symbol in symbols], 0.0, 0.45)
    keep = set(np.asarray(indices).reshape(-1).tolist())
    return [symbol for index, symbol in enumerate(symbols) if index in keep]


def detect_symbols(data: bytes, project: Project, *, tiles=()) -> list[Symbol]:
    """Detect symbols in an image, optionally on overlapping tiles."""
    model_path = os.environ.get("DETECTOR_MODEL_PATH", "models/detector.pt")
    image = _load_image_np(data)
    if image is None:
        project.meta["detector_backend"] = "invalid_image"
        return []

    backend = "heuristic_cv"
    symbols = None
    if Path(model_path).exists():
        try:
            from ultralytics import YOLO

            model = YOLO(model_path)
            symbols = _predict_regions(image, lambda tile: _yolo_symbols(model, tile), tiles)
            backend = "ultralytics_yolo"
        except Exception as exc:
            logger.warning("YOLO prediction failed; falling back to OpenCV: %s", exc)
    if symbols is None:
        symbols = _predict_regions(image, _heuristic, tiles)
    project.meta["detector_backend"] = backend
    project.meta["detector_tiles"] = max(1, len(tiles))
    for symbol in symbols:
        symbol.x = round(symbol.x * project.scale, 2)
        symbol.y = round(symbol.y * project.scale, 2)
        symbol.attributes["bbox"] = [round(value, 1) for value in symbol.attributes["bbox"]]
    logger.info("Detector identified %d symbols", len(symbols))
    return symbols
