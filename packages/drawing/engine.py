"""
packages/drawing/engine.py — High-level drawing engine for creating, modifying, and exporting DXF.
Used by the MCP server and pipeline output exporters.
"""

from __future__ import annotations

import io
import math
from typing import Any

import ezdxf

from packages.drawing.blocks import register_blocks
from packages.schema import Project, Symbol, SymbolType

STANDARD_LAYERS = {
    "IMJAN-SYMBOLEN": 7,    # White
    "IMJAN-KABELS": 1,      # Red
    "IMJAN-MAAT": 3,        # Green
    "IMJAN-TEKST": 4,       # Cyan
    "A-WANDEN": 8,          # Dark gray
}


def create_drawing(name: str = "", scale: float = 1.0) -> Any:
    """Creates a new DXF document configured with standard layers and block libraries."""
    doc = ezdxf.new("R2010", setup=True)
    for layer_name, color in STANDARD_LAYERS.items():
        if layer_name not in doc.layers:
            doc.layers.add(layer_name, color=color)

    register_blocks(doc)
    return doc


def place_symbol(doc: Any, symbol: Symbol) -> Symbol:
    """Places an electrical symbol block reference into the modelspace."""
    block_name = f"IMJAN-{symbol.type.value.upper()}"
    if block_name not in doc.blocks:
        # Fallback to generic block if specific variant is missing
        block_name = "IMJAN-WANDCONTACTDOOS"

    msp = doc.modelspace()
    rotation = float(symbol.attributes.get("rotation", 0.0))
    msp.add_blockref(
        block_name,
        insert=(symbol.x, symbol.y),
        dxfattribs={
            "layer": "IMJAN-SYMBOLEN",
            "rotation": rotation,
        },
    )

    if symbol.circuit:
        msp.add_text(
            symbol.circuit,
            dxfattribs={
                "layer": "IMJAN-TEKST",
                "height": 100.0,
                "insert": (symbol.x + 160.0, symbol.y + 100.0),
            },
        )
    return symbol


def draw_cable(
    doc: Any,
    points: list[tuple[float, float]],
    layer: str = "IMJAN-KABELS",
    circuit: str = "",
) -> float:
    """
    Draws a cable route polyline and calculates its real length in mm.
    """
    if len(points) < 2:
        return 0.0

    msp = doc.modelspace()
    msp.add_lwpolyline(points, dxfattribs={"layer": layer})

    # Calculate Euclidean length
    length = 0.0
    for i in range(len(points) - 1):
        length += math.hypot(points[i+1][0] - points[i][0], points[i+1][1] - points[i][1])

    if circuit:
        mid_idx = len(points) // 2
        mid_pt = points[mid_idx]
        msp.add_text(
            circuit,
            dxfattribs={
                "layer": "IMJAN-TEKST",
                "height": 80.0,
                "insert": (mid_pt[0] + 50.0, mid_pt[1] + 50.0),
            },
        )
    return length


def add_dimension(
    doc: Any,
    start: tuple[float, float],
    end: tuple[float, float],
    offset: float = 100.0,
) -> float:
    """Adds a linear dimension annotation between two points."""
    msp = doc.modelspace()
    dist = math.hypot(end[0] - start[0], end[1] - start[1])
    dim = msp.add_linear_dim(
        base=(start[0], start[1] - offset),
        p1=start,
        p2=end,
        dxfattribs={"layer": "IMJAN-MAAT"},
    )
    dim.render()
    return dist


def export_dxf(doc: Any) -> bytes:
    """Serializes DXF document to bytes."""
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def export_project_to_dxf(project: Project) -> bytes:
    """Converts a Project model into an exportable DXF drawing."""
    doc = create_drawing(name=project.name, scale=project.scale)
    msp = doc.modelspace()

    # Draw rooms
    for room in project.rooms:
        if len(room.polygon) >= 3:
            pts = [(p[0], p[1]) for p in room.polygon]
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "A-WANDEN"})
            # Room label in center
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            msp.add_text(
                room.name,
                dxfattribs={
                    "layer": "IMJAN-TEKST",
                    "height": 200.0,
                    "insert": (cx, cy),
                },
            )

    # Place symbols
    for sym in project.symbols:
        place_symbol(doc, sym)

    return export_dxf(doc)
