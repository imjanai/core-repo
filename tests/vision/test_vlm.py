"""
tests/vision/test_vlm.py — Unit tests for the VLM reasoning module.
"""

import pytest

from packages.schema import Project, SourceType, Symbol, SymbolType
from packages.vision.vlm import reason


def test_vlm_offline_graceful_fallback():
    # When vLLM server is not running, reason() should not crash, but return project intact
    proj = Project(
        symbols=[
            Symbol(type=SymbolType.ONBEKEND, x=100, y=100, confidence=0.5, source=SourceType.DETECTOR)
        ]
    )
    res = reason(proj, b"dummy_image_bytes", legend=[])
    assert res is not None
    assert len(res.symbols) == 1
    assert "vlm_status" in res.meta
