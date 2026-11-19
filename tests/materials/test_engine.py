"""
tests/materials/test_engine.py — unit-tests voor de materiaalengine.

Draaien:
    uv run pytest tests/materials/ -v
"""

from __future__ import annotations

import pytest

from packages.materials import compute_materials, get_entry, reload_catalogue
from packages.schema import Project, Symbol, SymbolType, SourceType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sym(
    sym_type: SymbolType,
    circuit: str | None = None,
    room_id: str | None = None,
) -> Symbol:
    return Symbol(
        type=sym_type,
        x=0.0,
        y=0.0,
        circuit=circuit,
        room_id=room_id,
        source=SourceType.VECTOR,
    )


def _project(*symbols: Symbol) -> Project:
    return Project(symbols=list(symbols))


# ---------------------------------------------------------------------------
# Catalogus
# ---------------------------------------------------------------------------


def test_catalogue_loads_all_types():
    """Elke SymbolType moet een entry hebben (of val terug op onbekend)."""
    for st in SymbolType:
        entry = get_entry(st.value)
        assert entry["description"], f"Geen omschrijving voor {st}"


def test_catalogue_unknown_fallback():
    entry = get_entry("bestaat_niet")
    assert entry["symbol_type"] == "onbekend"


def test_catalogue_reload():
    reload_catalogue()
    entry = get_entry("wandcontactdoos")
    assert entry["etim_code"] == "EC000195"


# ---------------------------------------------------------------------------
# Leeg project
# ---------------------------------------------------------------------------


def test_empty_project_gives_empty_materials():
    p = compute_materials(Project())
    assert p.materials == []


# ---------------------------------------------------------------------------
# Basismapping symbool → artikel
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sym_type, expected_etim",
    [
        (SymbolType.WANDCONTACTDOOS, "EC000195"),
        (SymbolType.SCHAKELAAR, "EC000194"),
        (SymbolType.LICHTPUNT, "EC001714"),
        (SymbolType.NOODVERLICHTING, "EC001716"),
        (SymbolType.VERDELER, "EC000334"),
        (SymbolType.GROEPENKAST, "EC000335"),
        (SymbolType.THERMOSTAAT, "EC000479"),
        (SymbolType.ROOKMELDER, "EC001069"),
        (SymbolType.DATAPUNT, "EC001553"),
    ],
)
def test_symbol_maps_to_correct_etim(sym_type, expected_etim):
    p = compute_materials(_project(_sym(sym_type)))
    main_lines = [l for l in p.materials if l.symbol_id != "ancillary"]
    etim_codes = [l.etim_code for l in main_lines]
    assert expected_etim in etim_codes, (
        f"{sym_type} moest ETIM {expected_etim} geven, maar kreeg: {etim_codes}"
    )


# ---------------------------------------------------------------------------
# Groepering en hoeveelheden
# ---------------------------------------------------------------------------


def test_quantity_aggregation():
    """3 WCD's in dezelfde groep/ruimte → 1 regel met quantity=3."""
    symbols = [_sym(SymbolType.WANDCONTACTDOOS, circuit="G1", room_id="r1") for _ in range(3)]
    p = compute_materials(_project(*symbols))
    wcd_lines = [l for l in p.materials if l.symbol_type == SymbolType.WANDCONTACTDOOS]
    assert len(wcd_lines) == 1
    assert wcd_lines[0].quantity == 3


def test_different_circuits_get_separate_lines():
    """Zelfde type, 2 verschillende groepen → 2 regels."""
    s1 = _sym(SymbolType.WANDCONTACTDOOS, circuit="G1")
    s2 = _sym(SymbolType.WANDCONTACTDOOS, circuit="G2")
    p = compute_materials(_project(s1, s2))
    wcd_lines = [l for l in p.materials if l.symbol_type == SymbolType.WANDCONTACTDOOS]
    assert len(wcd_lines) == 2


def test_different_rooms_get_separate_lines():
    s1 = _sym(SymbolType.LICHTPUNT, room_id="keuken")
    s2 = _sym(SymbolType.LICHTPUNT, room_id="slaapkamer")
    p = compute_materials(_project(s1, s2))
    licht_lines = [l for l in p.materials if l.symbol_type == SymbolType.LICHTPUNT]
    assert len(licht_lines) == 2


# ---------------------------------------------------------------------------
# Prijzen
# ---------------------------------------------------------------------------


def test_total_price_is_unit_price_times_quantity():
    symbols = [_sym(SymbolType.SCHAKELAAR) for _ in range(5)]
    p = compute_materials(_project(*symbols))
    sch_lines = [l for l in p.materials if l.symbol_type == SymbolType.SCHAKELAAR]
    assert len(sch_lines) == 1
    line = sch_lines[0]
    assert line.quantity == 5
    assert line.unit_price == pytest.approx(6.75)
    assert line.total_price == pytest.approx(33.75)


def test_unknown_symbol_has_no_price():
    p = compute_materials(_project(_sym(SymbolType.ONBEKEND)))
    unk_lines = [
        l for l in p.materials
        if l.symbol_type == SymbolType.ONBEKEND and l.symbol_id != "ancillary"
    ]
    assert len(unk_lines) == 1
    assert unk_lines[0].unit_price is None
    assert unk_lines[0].total_price is None


# ---------------------------------------------------------------------------
# Installatiebenodigdheden (ancillary)
# ---------------------------------------------------------------------------


def test_cable_nym_generated_for_power_symbols():
    symbols = [_sym(SymbolType.WANDCONTACTDOOS), _sym(SymbolType.LICHTPUNT)]
    p = compute_materials(_project(*symbols))
    ancillary = [l for l in p.materials if l.symbol_id == "ancillary"]
    etims = [l.etim_code for l in ancillary]
    assert "EC000233" in etims, "NYM-J kabel ontbreekt"


def test_utp_cable_generated_for_data_symbols():
    p = compute_materials(_project(_sym(SymbolType.DATAPUNT)))
    ancillary = [l for l in p.materials if l.symbol_id == "ancillary"]
    etims = [l.etim_code for l in ancillary]
    assert "EC001489" in etims, "UTP-kabel ontbreekt"


def test_inbouwdoos_generated():
    p = compute_materials(_project(_sym(SymbolType.WANDCONTACTDOOS)))
    ancillary = [l for l in p.materials if l.symbol_id == "ancillary"]
    etims = [l.etim_code for l in ancillary]
    assert "EC000196" in etims, "Inbouwdoos ontbreekt"


def test_circuit_breaker_generated_per_circuit():
    """2 circuits → 2 installatieautomaten."""
    symbols = [
        _sym(SymbolType.WANDCONTACTDOOS, circuit="G1"),
        _sym(SymbolType.WANDCONTACTDOOS, circuit="G2"),
    ]
    p = compute_materials(_project(*symbols))
    zek = [l for l in p.materials if l.etim_code == "EC000189"]
    assert len(zek) == 1
    assert zek[0].quantity == 2


def test_rcd_1_per_4_circuits():
    """4 circuits → 1 aardlekschakelaar; 5 circuits → 2."""
    symbols_4 = [_sym(SymbolType.LICHTPUNT, circuit=f"G{i}") for i in range(1, 5)]
    p4 = compute_materials(_project(*symbols_4))
    diff4 = [l for l in p4.materials if l.etim_code == "EC000191"]
    assert diff4[0].quantity == 1

    symbols_5 = [_sym(SymbolType.LICHTPUNT, circuit=f"G{i}") for i in range(1, 6)]
    p5 = compute_materials(_project(*symbols_5))
    diff5 = [l for l in p5.materials if l.etim_code == "EC000191"]
    assert diff5[0].quantity == 2


# ---------------------------------------------------------------------------
# Sortering
# ---------------------------------------------------------------------------


def test_output_is_sorted():
    symbols = [
        _sym(SymbolType.ROOKMELDER),
        _sym(SymbolType.WANDCONTACTDOOS),
        _sym(SymbolType.LICHTPUNT),
    ]
    p = compute_materials(_project(*symbols))
    descriptions = [l.description for l in p.materials if l.symbol_id != "ancillary"]
    assert descriptions == sorted(descriptions)


# ---------------------------------------------------------------------------
# Idempotentie
# ---------------------------------------------------------------------------


def test_compute_materials_is_idempotent():
    """Twee keer aanroepen geeft dezelfde lijst."""
    symbols = [_sym(SymbolType.SCHAKELAAR), _sym(SymbolType.LICHTPUNT)]
    p = _project(*symbols)
    p1 = compute_materials(p.model_copy(deep=True))
    p2 = compute_materials(p.model_copy(deep=True))
    assert [l.model_dump() for l in p1.materials] == [l.model_dump() for l in p2.materials]
