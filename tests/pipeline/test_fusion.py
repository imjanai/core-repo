"""
tests/pipeline/test_fusion.py — de fusiestap (stap 6) los getest.

Draaien:
    uv run pytest tests/pipeline/test_fusion.py -v
"""

from __future__ import annotations

from packages.pipeline.fusion import FusionConfig, fuse, point_in_polygon
from packages.schema import Project, Room, Symbol, SymbolType


def sym(
    sym_type: SymbolType = SymbolType.WANDCONTACTDOOS,
    x: float = 1000.0,
    y: float = 1000.0,
    confidence: float = 1.0,
    source: str = "vector",
    room_id: str | None = None,
    circuit: str | None = None,
) -> Symbol:
    return Symbol(
        type=sym_type,
        x=x,
        y=y,
        confidence=confidence,
        source=source,  # type: ignore[arg-type]
        room_id=room_id,
        circuit=circuit,
    )


def room(name: str, polygon: list[list[float]]) -> Room:
    return Room(name=name, polygon=polygon)


# ---------------------------------------------------------------------------
# Samensmelten
# ---------------------------------------------------------------------------


def test_symbols_within_distance_are_merged():
    p = Project(symbols=[sym(x=1000, y=1000), sym(x=1080, y=1040, source="detector", confidence=0.8)])
    p, stats = fuse(p)

    assert stats.input_count == 2
    assert stats.output_count == 1
    assert stats.merged == 1
    assert len(p.symbols) == 1


def test_merged_symbol_keeps_provenance_and_boosts_confidence():
    p = Project(symbols=[sym(x=1000, y=1000), sym(x=1100, y=1000, source="vlm", confidence=0.7)])
    p, _ = fuse(p)

    s = p.symbols[0]
    assert s.confidence >= 0.9  # bevestiging door twee sporen
    assert set(s.attributes["sources"]) == {"vector", "vlm"}
    assert len(s.attributes["merged_from"]) == 1
    assert s.source.value == "vector"  # vector wint van vlm


def test_symbols_on_praktische_wandafstand_staan_uit_elkaar():
    """Twee WCD's 400 mm uit elkaar (gangbare muurafstand) zijn twee stuks."""
    p = Project(symbols=[sym(x=1000, y=1000), sym(x=1400, y=1000)])
    p, stats = fuse(p)
    assert stats.output_count == 2
    assert stats.merged == 0


def test_fusieafstand_is_configurabel():
    """Wil je agressiever samensmelten (bv. alleen cross- spoors)? Drempel omlaag."""
    cfg = FusionConfig(merge_distance_mm=50.0)
    p = Project(symbols=[sym(x=1000, y=1000), sym(x=1080, y=1040)])
    p, stats = fuse(p, cfg)
    assert stats.output_count == 2


def test_different_types_never_merge():
    p = Project(
        symbols=[
            sym(SymbolType.WANDCONTACTDOOS, x=1000, y=1000),
            sym(SymbolType.LICHTPUNT, x=1010, y=1000),
        ]
    )
    p, stats = fuse(p)
    assert stats.output_count == 2


def test_merged_position_is_confidence_weighted():
    """De zekerder herkende bron bepaalt waar het symbool komt te liggen."""
    p = Project(
        symbols=[
            sym(x=1000, y=1000, confidence=1.0, source="vector"),
            sym(x=1140, y=1000, confidence=0.4, source="detector"),
        ]
    )
    p, stats = fuse(p)
    assert stats.merged == 1
    x = p.symbols[0].x
    # Dichter bij de vector-vondst (1000) dan bij de detector (1140)
    assert abs(x - 1000) < abs(x - 1140)
    assert 1000 < x < 1140  # wel een gewogen gemiddelde, niet de beste bron


# ---------------------------------------------------------------------------
# Ruis filteren
# ---------------------------------------------------------------------------


def test_low_confidence_detector_output_dropped():
    p = Project(symbols=[sym(confidence=0.1, source="detector")])
    p, stats = fuse(p)
    assert stats.output_count == 0
    assert stats.dropped_low_confidence == 1
    assert p.meta["fusion"]["dropped_ids"]


def test_vector_output_is_always_trusted():
    p = Project(symbols=[sym(confidence=0.01, source="vector")])
    p, stats = fuse(p)
    assert stats.output_count == 1
    assert stats.dropped_low_confidence == 0


def test_human_correction_is_always_trusted():
    p = Project(symbols=[sym(confidence=0.0, source="human")])
    _, stats = fuse(p)
    assert stats.output_count == 1


def test_drempel_configurabel():
    cfg = FusionConfig(min_confidence=0.9)
    p = Project(symbols=[sym(confidence=0.5, source="detector")])
    p, stats = fuse(p, cfg)
    assert stats.output_count == 0


# ---------------------------------------------------------------------------
# Ruimtestoebedeling
# ---------------------------------------------------------------------------


def test_symbol_inside_room_gets_room_id():
    r = room("Keuken", [[0, 0], [4000, 0], [4000, 3000], [0, 3000]])
    p = Project(rooms=[r], symbols=[sym(x=2000, y=1500)])
    p, stats = fuse(p)
    assert p.symbols[0].room_id == r.id
    assert stats.rooms_assigned == 1


def test_symbol_outside_rooms_stays_unassigned():
    r = room("Keuken", [[0, 0], [1000, 0], [1000, 1000], [0, 1000]])
    p = Project(rooms=[r], symbols=[sym(x=9000, y=9000)])
    p, stats = fuse(p)
    assert p.symbols[0].room_id is None
    assert stats.rooms_assigned == 0


def test_existing_room_id_is_preserved():
    r = room("Keuken", [[0, 0], [4000, 0], [4000, 3000], [0, 3000]])
    other = room("Badkamer", [[5000, 0], [9000, 0], [9000, 3000], [5000, 3000]])
    p = Project(rooms=[r, other], symbols=[sym(x=2000, y=1500, room_id=other.id)])
    p, _ = fuse(p)
    assert p.symbols[0].room_id == other.id


def test_merging_inherits_room_from_other_spoor():
    r = room("Woonkamer", [[0, 0], [6000, 0], [6000, 4000], [0, 4000]])
    p = Project(
        rooms=[r],
        symbols=[
            sym(x=1000, y=1000),                       # geen ruimte
            sym(x=1050, y=1000, source="vlm", room_id=r.id),
        ],
    )
    p, _ = fuse(p)
    assert p.symbols[0].room_id == r.id


# ---------------------------------------------------------------------------
# point_in_polygon
# ---------------------------------------------------------------------------


def test_point_in_polygon_inside():
    square = [[0, 0], [10, 0], [10, 10], [0, 10]]
    assert point_in_polygon(5, 5, square)
    assert not point_in_polygon(15, 5, square)
    assert not point_in_polygon(-1, 5, square)


def test_point_in_polygon_concave():
    # L-vorm
    l_shape = [[0, 0], [10, 0], [10, 4], [4, 4], [4, 10], [0, 10]]
    assert point_in_polygon(2, 2, l_shape)   # in de poot
    assert point_in_polygon(2, 8, l_shape)   # in de staart
    assert not point_in_polygon(8, 8, l_shape)  # in de inkeping


def test_point_in_polygon_invalid_polygon():
    assert not point_in_polygon(1, 1, [])
    assert not point_in_polygon(1, 1, [[0, 0], [1, 1]])
