"""
tests/parsers/test_pdf.py — Unit tests for the PDF parser.
"""

import pymupdf
import pytest

from packages.parsers.pdf import parse_pdf
from packages.schema import FileType


def test_parse_pdf_basic():
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    # Draw sample small circle (symbol)
    page.draw_circle((150, 200), radius=6)
    page.insert_text((150, 220), "WCD", fontsize=10)
    page.insert_text((300, 300), "Woonkamer", fontsize=14)
    page.insert_text((400, 750), "Schaal 1:100", fontsize=10)

    pdf_bytes = doc.tobytes()
    parsed = parse_pdf(pdf_bytes)

    assert parsed.file_type == FileType.PDF
    assert parsed.scale == 100.0
    assert len(parsed.rooms) >= 1
    assert any("woonkamer" in r.name.lower() for r in parsed.rooms)
    assert len(parsed.symbols) >= 1


def test_parse_pdf_empty():
    parsed = parse_pdf(b"")
    assert parsed.file_type == FileType.PDF
