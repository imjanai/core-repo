"""
packages/parsers/pdf.py — PDF parser combining PyMuPDF and pdfplumber.
Handles both vector-CAD PDFs and raster/scanned blueprints.
"""

from __future__ import annotations

import io
import logging
import math
import re
from typing import Any

import pdfplumber
import pymupdf

from packages.schema import FileType, Project, Room, SourceType, Symbol, SymbolType

logger = logging.getLogger("imjan.parsers.pdf")

TEXT_SYMBOL_MAP: list[tuple[re.Pattern[str], SymbolType]] = [
    (re.compile(r"\b(wcd.*dubbel|dubbel.*wcd)\b", re.IGNORECASE), SymbolType.WANDCONTACTDOOS_DUBBEL),
    (re.compile(r"\b(wcd|stopcontact)\b", re.IGNORECASE), SymbolType.WANDCONTACTDOOS),
    (re.compile(r"\b(schakelaar|sch\b|wissel|kruis)\b", re.IGNORECASE), SymbolType.SCHAKELAAR),
    (re.compile(r"\b(lichtpunt|lamp|armatuur|spot)\b", re.IGNORECASE), SymbolType.LICHTPUNT),
    (re.compile(r"\b(data|rj45|netwerk)\b", re.IGNORECASE), SymbolType.DATAPUNT),
    (re.compile(r"\b(verdeler|kast|zekeringkast|bord)\b", re.IGNORECASE), SymbolType.VERDELER),
    (re.compile(r"\b(rookmelder|rm\b)\b", re.IGNORECASE), SymbolType.ROOKMELDER),
    (re.compile(r"\b(thermostaat|th\b)\b", re.IGNORECASE), SymbolType.THERMOSTAAT),
]

ROOM_NAMES = [
    "woonkamer", "leefruimte", "salon", "keuken", "slaapkamer", "badkamer",
    "toilet", "wc", "gang", "hal", "inkom", "berging", "wasplaats",
    "bureau", "garage", "zolder", "kelder", "terras", "meterkast",
]

SCALE_REGEX = re.compile(r"(?:schaal|scale)\s*[:=]?\s*1\s*[:/]\s*(\d+)", re.IGNORECASE)


def parse_pdf(data: bytes) -> Project:
    """
    Parses a PDF file from bytes.
    Extracts vector geometric primitives, text labels, and detects scale.
    """
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        logger.error("Failed to open PDF with PyMuPDF: %s", exc)
        return Project(file_type=FileType.PDF, meta={"error": str(exc)})

    if len(doc) == 0:
        return Project(file_type=FileType.PDF, meta={"empty": True})

    page0 = doc[0]
    drawings = page0.get_drawings()
    images = page0.get_images()

    is_vector = len(drawings) > 10 or (len(images) == 0 and len(drawings) > 0)
    page_rect = page0.rect
    width_pt, height_pt = page_rect.width, page_rect.height

    # Convert pt (1/72 inch) to mm (1 pt = 0.352778 mm)
    pt_to_mm = 0.352778

    # Extract text words and positions using pdfplumber
    words_data: list[dict[str, Any]] = []
    scale = 1.0

    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if len(pdf.pages) > 0:
                p0 = pdf.pages[0]
                extracted_words = p0.extract_words()
                for w in extracted_words:
                    words_data.append({
                        "text": w["text"],
                        "x": float(w["x0"]) * pt_to_mm,
                        "y": float(w["top"]) * pt_to_mm,
                    })

                full_text = p0.extract_text() or ""
                scale_match = SCALE_REGEX.search(full_text)
                if scale_match:
                    scale_val = float(scale_match.group(1))
                    scale = scale_val  # e.g. 1:100 scale
    except Exception as exc:
        logger.debug("pdfplumber word extraction error: %s", exc)

    rooms: list[Room] = []
    symbols: list[Symbol] = []

    # 1. Detect rooms from text annotations
    for w in words_data:
        text_lower = w["text"].lower()
        if any(rn in text_lower for rn in ROOM_NAMES):
            rooms.append(
                Room(
                    name=w["text"],
                    polygon=[
                        [w["x"] - 500, w["y"] - 500],
                        [w["x"] + 500, w["y"] - 500],
                        [w["x"] + 500, w["y"] + 500],
                        [w["x"] - 500, w["y"] + 500],
                    ],
                )
            )

    # 2. Extract vector primitives as candidate symbols
    # In CAD PDFs, symbols are usually small circles or small rects (size between 2mm and 15mm)
    candidate_shapes: list[dict[str, Any]] = []
    for d in drawings:
        rect = d.get("rect")
        if not rect:
            continue
        rw = (rect[2] - rect[0]) * pt_to_mm
        rh = (rect[3] - rect[1]) * pt_to_mm
        cx = (rect[0] + rect[2]) / 2.0 * pt_to_mm
        cy = (rect[1] + rect[3]) / 2.0 * pt_to_mm

        # Filter typical symbol bounding box sizes in drawing mm
        if 1.5 <= rw <= 25.0 and 1.5 <= rh <= 25.0:
            candidate_shapes.append({"x": cx, "y": cy, "w": rw, "h": rh})

    # Cluster or associate shapes with nearest text
    for shape in candidate_shapes:
        sx, sy = shape["x"], shape["y"]
        matched_type = SymbolType.ONBEKEND
        circuit = None

        # Check for nearby text annotation (within 15mm)
        for w in words_data:
            dist = math.hypot(w["x"] - sx, w["y"] - sy)
            if dist < 15.0:
                for pat, st in TEXT_SYMBOL_MAP:
                    if pat.search(w["text"]):
                        matched_type = st
                        break
                if re.match(r"^G\d+$", w["text"], re.IGNORECASE):
                    circuit = w["text"].upper()

        if matched_type != SymbolType.ONBEKEND or len(candidate_shapes) < 50:
            sym = Symbol(
                type=matched_type,
                x=round(sx, 2),
                y=round(sy, 2),
                circuit=circuit,
                confidence=0.85 if matched_type != SymbolType.ONBEKEND else 0.5,
                source=SourceType.VECTOR,
                attributes={"shape": "vector_drawing"},
            )
            symbols.append(sym)

    meta = {
        "parser": "pdfplumber+pymupdf",
        "is_vector": is_vector,
        "pages": len(doc),
        "width_pt": width_pt,
        "height_pt": height_pt,
        "candidate_shapes": len(candidate_shapes),
        "total_symbols": len(symbols),
        "total_rooms": len(rooms),
        "scale": scale,
    }

    return Project(
        file_type=FileType.PDF,
        scale=scale,
        rooms=rooms,
        symbols=symbols,
        meta=meta,
    )
