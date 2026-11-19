"""
tests/pipeline/test_exporters.py — Unit tests for pipeline output exporters (Excel, PDF, DXF).
"""

import pytest

from packages.pipeline.exporters import (
    export_materials_excel,
    export_project_dxf,
    export_quote_pdf,
)
from packages.schema import MaterialLine, Project, Room, Symbol, SymbolType, ValidationWarning


@pytest.fixture
def sample_project() -> Project:
    return Project(
        name="Woning Test Exporters",
        rooms=[
            Room(name="Woonkamer", polygon=[[0, 0], [5000, 0], [5000, 4000], [0, 4000]])
        ],
        symbols=[
            Symbol(type=SymbolType.WANDCONTACTDOOS, x=1000, y=1000, circuit="G1"),
            Symbol(type=SymbolType.SCHAKELAAR, x=2000, y=1000, circuit="G1"),
        ],
        materials=[
            MaterialLine(
                symbol_id="s1",
                symbol_type=SymbolType.WANDCONTACTDOOS,
                description="Wandcontactdoos 2P+A inbouw",
                quantity=4,
                unit="st",
                unit_price=8.50,
                total_price=34.00,
            ),
            MaterialLine(
                symbol_id="s2",
                symbol_type=SymbolType.SCHAKELAAR,
                description="Enkelpolige schakelaar inbouw",
                quantity=2,
                unit="st",
                unit_price=6.20,
                total_price=12.40,
            ),
        ],
        warnings=[
            ValidationWarning(code="TEST-WARN", severity="warning", message="Controleer leidinglengte")
        ],
    )


def test_export_materials_excel(sample_project: Project):
    excel_bytes = export_materials_excel(sample_project)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0
    # Check for zip/excel magic header PK
    assert excel_bytes.startswith(b"PK")


def test_export_quote_pdf(sample_project: Project):
    pdf_bytes = export_quote_pdf(sample_project)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


def test_export_project_dxf(sample_project: Project):
    dxf_bytes = export_project_dxf(sample_project)
    assert isinstance(dxf_bytes, bytes)
    assert len(dxf_bytes) > 0
    assert b"SECTION" in dxf_bytes
