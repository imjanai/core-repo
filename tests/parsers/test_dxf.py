"""
tests/parsers/test_dxf.py — Unit tests for the DXF parser.
"""

import io
import ezdxf
import pytest

from packages.parsers.dxf import parse_dxf
from packages.schema import FileType, SymbolType


def test_parse_dxf_simple():
    doc = ezdxf.new("R2010")
    # Expliciet: ezdxf laat $INSUNITS op 6 (meter) staan. De parser zet alles
    # om naar millimeters, dus de kringtekst moet binnen 2000 mm van het
    # symbool staan — net als op een echte tekening, waar het groepsnummer
    # vlak naast de contactdoos wordt gezet.
    doc.header["$INSUNITS"] = 6
    msp = doc.modelspace()

    # Define a sample block
    blk = doc.blocks.new("WCD_STANDAARD")
    blk.add_circle((0, 0), radius=10)

    # Insert two symbols
    msp.add_blockref("WCD_STANDAARD", (100.0, 200.0))
    msp.add_blockref("WCD_STANDAARD", (300.0, 400.0))

    # Add text label for room and circuit (G1 staat 0,42 eenheid = 424 mm van
    # de eerste WCD; de tweede WCD ligt honderden meters verderop)
    msp.add_text("Woonkamer", dxfattribs={"insert": (200.0, 300.0)})
    msp.add_text("G1", dxfattribs={"insert": (100.3, 200.3)})

    stream = io.StringIO()
    doc.write(stream)
    dxf_bytes = stream.getvalue().encode("utf-8")

    project = parse_dxf(dxf_bytes)
    assert project.file_type == FileType.DXF
    assert len(project.symbols) == 2
    assert project.symbols[0].type == SymbolType.WANDCONTACTDOOS
    assert len(project.rooms) >= 1
    assert project.rooms[0].name == "Woonkamer"
    assert project.symbols[0].circuit == "G1"
    # De tweede WCD hoort niet bij die kringlabel: die hoort bij de eerste.
    assert project.symbols[1].circuit is None


def test_kringlabel_buiten_2m_wordt_niet_toegevoegd():
    """De kringassociatie heeft een straal van 2000 mm — verder weg is het
    groepsnummer van iemand anders, en een verkeerde kring is erger dan geen."""
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 6  # meter, zoals ezdxf standaard doet
    msp = doc.modelspace()
    blk = doc.blocks.new("WCD_STANDAARD")
    blk.add_circle((0, 0), radius=10)

    msp.add_blockref("WCD_STANDAARD", (0.0, 0.0))
    msp.add_text("G2", dxfattribs={"insert": (3.0, 0.0)})  # 3 m verderop

    buf = io.StringIO()
    doc.write(buf)
    project = parse_dxf(buf.getvalue().encode("utf-8"))

    assert len(project.symbols) == 1
    assert project.symbols[0].circuit is None


def test_parse_dxf_corrupt_bytes():
    project = parse_dxf(b"NOT A REAL DXF CONTENT")
    assert project.file_type == FileType.DXF
