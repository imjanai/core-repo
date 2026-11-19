"""
tests/drawing/test_engine.py — Unit tests for the DXF drawing engine.
"""

import pytest

from packages.drawing import (
    add_dimension,
    create_drawing,
    draw_cable,
    export_dxf,
    export_project_to_dxf,
    place_symbol,
)
from packages.schema import Project, Room, Symbol, SymbolType


def test_drawing_lifecycle():
    doc = create_drawing(name="Test Plan")
    assert "IMJAN-SYMBOLEN" in doc.layers
    assert "IMJAN-KABELS" in doc.layers

    # Place symbol
    sym = Symbol(type=SymbolType.WANDCONTACTDOOS, x=1000.0, y=2000.0, circuit="G1")
    placed = place_symbol(doc, sym)
    assert placed.circuit == "G1"

    # Draw cable
    length = draw_cable(doc, [(1000.0, 2000.0), (1000.0, 3000.0), (2000.0, 3000.0)], circuit="G1")
    assert length == 2000.0

    # Dimension
    dist = add_dimension(doc, (1000.0, 2000.0), (1000.0, 3000.0))
    assert dist == 1000.0

    # Export to bytes
    dxf_data = export_dxf(doc)
    assert isinstance(dxf_data, bytes)
    assert len(dxf_data) > 0


def test_export_project_to_dxf():
    proj = Project(
        name="Project Export Test",
        rooms=[
            Room(name="Woonkamer", polygon=[[0, 0], [4000, 0], [4000, 3000], [0, 3000]])
        ],
        symbols=[
            Symbol(type=SymbolType.WANDCONTACTDOOS, x=1500, y=1000, circuit="G1"),
            Symbol(type=SymbolType.SCHAKELAAR, x=2500, y=1000, circuit="G1"),
        ],
    )
    dxf_bytes = export_project_to_dxf(proj)
    assert len(dxf_bytes) > 0
    assert b"SECTION" in dxf_bytes
