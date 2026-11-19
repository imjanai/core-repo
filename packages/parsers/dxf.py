"""
packages/parsers/dxf.py — DXF parser using ezdxf.
Extracts symbols, layers, rooms, circuits, and scale from DXF files.
"""

from __future__ import annotations

import io
import logging
import math
import re
from typing import Any

import ezdxf

from packages.schema import FileType, Project, Room, SourceType, Symbol, SymbolType

logger = logging.getLogger("imjan.parsers.dxf")

# Standard AutoCAD $INSUNITS mapping to millimeters
INSUNITS_SCALE_TO_MM: dict[int, float] = {
    0: 1.0,      # Unspecified -> default 1:1 mm
    1: 25.4,     # Inches
    2: 304.8,    # Feet
    3: 1609344,  # Miles
    4: 1.0,      # Millimeters
    5: 10.0,     # Centimeters
    6: 1000.0,   # Meters
    7: 1000000,  # Kilometers
}

# Semantic mapping from block names / layers to SymbolType
BLOCK_TYPE_MAP: list[tuple[re.Pattern[str], SymbolType]] = [
    # Special double/waterproof sockets
    (re.compile(r"(wcd.*dubbel|dubbel.*wcd|socket.*double)", re.IGNORECASE), SymbolType.WANDCONTACTDOOS_DUBBEL),
    (re.compile(r"(wcd.*(waterdicht|ip|wp)|socket.*waterproof)", re.IGNORECASE), SymbolType.WANDCONTACTDOOS_WATERDICHT),
    (re.compile(r"(wcd.*(kracht|3p|400v)|krachtstroom|power.*socket)", re.IGNORECASE), SymbolType.WANDCONTACTDOOS_KRACHT),
    (re.compile(r"(wcd|stopcontact|socket|outlet|wandcontactdoos)", re.IGNORECASE), SymbolType.WANDCONTACTDOOS),

    # Switches
    (re.compile(r"(schakelaar.*wissel|wisselschakelaar|switch.*toggle)", re.IGNORECASE), SymbolType.SCHAKELAAR_WISSEL),
    (re.compile(r"(schakelaar.*kruis|kruisschakelaar)", re.IGNORECASE), SymbolType.SCHAKELAAR_KRUIS),
    (re.compile(r"(schakelaar.*dimmer|dimmer)", re.IGNORECASE), SymbolType.SCHAKELAAR_DIMMER),
    (re.compile(r"(schakelaar|switch|interrupteur)", re.IGNORECASE), SymbolType.SCHAKELAAR),
    (re.compile(r"(drukknop|pushbutton|push.*button)", re.IGNORECASE), SymbolType.DRUKKNOP),
    (re.compile(r"(bewegingsmelder|pir|motion)", re.IGNORECASE), SymbolType.BEWEGINGSMELDER),

    # Lighting
    (re.compile(r"(spot|inbouwspot|downlight)", re.IGNORECASE), SymbolType.LICHTPUNT_SPOT),
    (re.compile(r"(tl|fluorescent|led.*balk)", re.IGNORECASE), SymbolType.LICHTPUNT_TL),
    (re.compile(r"(buitenverlichting|lichtpunt.*buiten)", re.IGNORECASE), SymbolType.LICHTPUNT_BUITEN),
    (re.compile(r"(noodverlichting.*pictogram|vluchtweg)", re.IGNORECASE), SymbolType.NOODVERLICHTING_PICTOGRAM),
    (re.compile(r"(noodverlichting|emergency.*light)", re.IGNORECASE), SymbolType.NOODVERLICHTING),
    (re.compile(r"(lichtpunt|lamp|armatuur|licht|light)", re.IGNORECASE), SymbolType.LICHTPUNT),

    # Safety & sensors
    (re.compile(r"(rookmelder|smoke.*detector)", re.IGNORECASE), SymbolType.ROOKMELDER),
    (re.compile(r"(koolmonoxidemelder|co.*melder)", re.IGNORECASE), SymbolType.KOOLMONOXIDEMELDER),
    (re.compile(r"(hittemelder|heat.*detector)", re.IGNORECASE), SymbolType.HITTEMELDER),
    (re.compile(r"(gasdetector|gas.*detector)", re.IGNORECASE), SymbolType.GASDETECTOR),

    # Distribution & panels
    (re.compile(r"(groepenkast|hoofdverdeelkast|main.*panel)", re.IGNORECASE), SymbolType.GROEPENKAST),
    (re.compile(r"(verdeler|zekeringkast|schakelkast|distribution.*board|panel)", re.IGNORECASE), SymbolType.VERDELER),

    # Data & comms
    (re.compile(r"(datapunt.*dubbel|rj45.*dubbel|data.*double)", re.IGNORECASE), SymbolType.DATAPUNT_DUBBEL),
    (re.compile(r"(datapunt|rj45|netwerk|ethernet|data)", re.IGNORECASE), SymbolType.DATAPUNT),
    (re.compile(r"(tv|coax|cai)", re.IGNORECASE), SymbolType.TV_PUNT),
    (re.compile(r"(thermostaat|thermostat)", re.IGNORECASE), SymbolType.THERMOSTAAT),
    (re.compile(r"(laadpaal|ev.*charger|wallbox)", re.IGNORECASE), SymbolType.LAADPAAL),
    (re.compile(r"(intercom|videofoon)", re.IGNORECASE), SymbolType.INTERCOM),
]

LAYER_TYPE_MAP: list[tuple[re.Pattern[str], SymbolType]] = [
    (re.compile(r"(e-.*wcd|elec.*socket|stopcontact)", re.IGNORECASE), SymbolType.WANDCONTACTDOOS),
    (re.compile(r"(e-.*schakelaar|elec.*switch)", re.IGNORECASE), SymbolType.SCHAKELAAR),
    (re.compile(r"(e-.*licht|elec.*light)", re.IGNORECASE), SymbolType.LICHTPUNT),
    (re.compile(r"(e-.*data|elec.*comm)", re.IGNORECASE), SymbolType.DATAPUNT),
    (re.compile(r"(e-.*verdeler|elec.*panel)", re.IGNORECASE), SymbolType.VERDELER),
    (re.compile(r"(e-.*brand|e-.*rook)", re.IGNORECASE), SymbolType.ROOKMELDER),
]

ROOM_NAME_PATTERNS = [
    "woonkamer", "leefruimte", "salon", "keuken", "slaapkamer", "badkamer",
    "toilet", "wc", "gang", "hal", "inkom", "berging", "wasplaats",
    "bureau", "kantoor", "garage", "zolder", "kelder", "terras", "technische ruimte",
]


def _match_symbol_type(name: str, layer: str) -> SymbolType:
    for pattern, st in BLOCK_TYPE_MAP:
        if pattern.search(name):
            return st
    for pattern, st in LAYER_TYPE_MAP:
        if pattern.search(layer):
            return st
    return SymbolType.ONBEKEND


def _decode_dxf_bytes(data: bytes) -> str:
    """Safely decodes DXF bytes with multi-encoding fallback."""
    for enc in ("utf-8", "cp1252", "latin1", "iso-8859-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def read_dxf(data: bytes) -> ezdxf.document.Drawing:
    """Read DXF text with universal newline handling, like ezdxf.readfile."""
    return ezdxf.read(io.StringIO(_decode_dxf_bytes(data), newline=None))


def parse_dxf(data: bytes) -> Project:
    """
    Parses a DXF file and returns a populated Project model.
    """
    try:
        doc = read_dxf(data)
    except Exception as exc:
        logger.error("Failed to parse DXF stream: %s", exc)
        return Project(file_type=FileType.DXF, meta={"error": str(exc)})

    # Determine unit scale to millimeters
    insunits = doc.header.get("$INSUNITS", 4)
    scale_factor = INSUNITS_SCALE_TO_MM.get(int(insunits), 1.0)

    msp = doc.modelspace()
    symbols: list[Symbol] = []
    rooms: list[Room] = []
    text_annotations: list[dict[str, Any]] = []

    # Read layers to identify disabled / frozen states
    hidden_layers = set()
    for layer in doc.layers:
        if layer.is_off() or layer.is_frozen():
            hidden_layers.add(layer.dxf.name)

    # 1. Extract TEXT and MTEXT entities (room names, circuits, scale strings)
    circuit_re = re.compile(r"\b(G\d+|Groep\s*\d+|Kring\s*[A-Z\d]+)\b", re.IGNORECASE)
    for text_ent in msp.query("TEXT MTEXT"):
        if text_ent.dxf.layer in hidden_layers:
            continue
        raw_text = getattr(text_ent.dxf, "text", "")
        if not raw_text and hasattr(text_ent, "plain_text"):
            raw_text = text_ent.plain_text()
        raw_text = raw_text.strip()
        if not raw_text:
            continue

        insert_pt = getattr(text_ent.dxf, "insert", (0.0, 0.0, 0.0))
        tx = float(insert_pt[0]) * scale_factor
        ty = float(insert_pt[1]) * scale_factor
        text_annotations.append({"text": raw_text, "x": tx, "y": ty})

        # Check if text is a room name
        lower_t = raw_text.lower()
        if any(rn in lower_t for rn in ROOM_NAME_PATTERNS):
            rooms.append(
                Room(
                    name=raw_text,
                    polygon=[
                        [tx - 1500, ty - 1500],
                        [tx + 1500, ty - 1500],
                        [tx + 1500, ty + 1500],
                        [tx - 1500, ty + 1500],
                    ],
                )
            )

    # 2. Extract INSERT entities (blocks)
    for insert in msp.query("INSERT"):
        layer = getattr(insert.dxf, "layer", "0")
        if layer in hidden_layers:
            continue
        name = getattr(insert.dxf, "name", "")
        pt = getattr(insert.dxf, "insert", (0.0, 0.0, 0.0))
        sx = float(pt[0]) * scale_factor
        sy = float(pt[1]) * scale_factor
        rotation = float(getattr(insert.dxf, "rotation", 0.0))

        sym_type = _match_symbol_type(name, layer)
        circuit = None

        # Look for closest circuit annotation within 2000mm radius
        closest_dist = 2000.0
        for ann in text_annotations:
            m = circuit_re.search(ann["text"])
            if m:
                d = math.hypot(ann["x"] - sx, ann["y"] - sy)
                if d < closest_dist:
                    closest_dist = d
                    circuit = m.group(1).upper()

        sym = Symbol(
            type=sym_type,
            x=round(sx, 2),
            y=round(sy, 2),
            circuit=circuit,
            confidence=1.0 if sym_type != SymbolType.ONBEKEND else 0.6,
            source=SourceType.VECTOR,
            attributes={
                "block_name": name,
                "layer": layer,
                "rotation": rotation,
            },
        )
        symbols.append(sym)

    # Assign room_id to symbols located inside room bounding boxes/polygons
    for sym in symbols:
        for r in rooms:
            if len(r.polygon) >= 3:
                xs = [p[0] for p in r.polygon]
                ys = [p[1] for p in r.polygon]
                if min(xs) <= sym.x <= max(xs) and min(ys) <= sym.y <= max(ys):
                    sym.room_id = r.id
                    break

    meta = {
        "parser": "ezdxf",
        "insunits": insunits,
        "scale_factor_to_mm": scale_factor,
        "total_inserts": len(symbols),
        "total_rooms": len(rooms),
        "layers": [layer.dxf.name for layer in doc.layers],
    }

    return Project(
        file_type=FileType.DXF,
        scale=scale_factor,
        rooms=rooms,
        symbols=symbols,
        meta=meta,
    )
