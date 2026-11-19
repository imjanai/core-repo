"""
tests/rules/test_engine.py — tests voor de geherstructureerde regelengine.

Draaien:
    uv run pytest tests/rules/ -v
"""

from __future__ import annotations

import pytest

from packages.rules import (
    validate, list_rules, disable_rule, enable_rule,
    DEFAULT_CONFIG, INDUSTRIAL_CONFIG, RulesConfig,
)
from packages.rules.limits import CircuitLimits, SafetyLimits, ProjectLimits
from packages.schema import Project, Room, Symbol, SymbolType, SourceType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sym(
    sym_type: SymbolType,
    x: float = 0.0,
    y: float = 0.0,
    circuit: str | None = None,
    room_id: str | None = None,
    **attrs,
) -> Symbol:
    return Symbol(
        type=sym_type, x=x, y=y,
        circuit=circuit, room_id=room_id,
        source=SourceType.VECTOR,
        attributes=attrs,
    )


def _room(name: str) -> Room:
    return Room(name=name)


def _project(*symbols: Symbol, rooms: list[Room] | None = None) -> Project:
    return Project(symbols=list(symbols), rooms=rooms or [])


def _codes(project: Project) -> set[str]:
    return {w.code for w in project.warnings}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_all_rule_modules_loaded():
    rules = list_rules()
    ids = {r["id"] for r in rules}
    # Ten minste de modules die we hebben geschreven
    expected = {
        "AREI-4.4.2-WCD", "AREI-4.4.2-LICHT", "AREI-4.4.3-KRACHT",
        "AREI-4-GROEP-LEEG", "AREI-4-ONGEGROEP",
        "AREI-6.4.1-DDR", "AREI-6.4.1-PANEL", "AREI-6-GRP-BEVEIL",
        "AREI-7-ROOK-SLAAP", "AREI-7-NOOD-GANG", "AREI-7-DUBBEL",
        "SCHEMA-PANEL-GROOT", "SCHEMA-SYM-ONBEKEND",
    }
    missing = expected - ids
    assert not missing, f"Regelmodules niet geladen: {missing}"


def test_list_rules_has_article_field():
    for r in list_rules():
        assert r["article"], f"Regel {r['id']} mist artikel-veld"


def test_list_rules_scope_filter():
    residential = {r["id"] for r in list_rules(scope="residential")}
    industrial = {r["id"] for r in list_rules(scope="industrial")}
    # AREI-4.4.3-KRACHT is alleen voor industrial/commercial
    assert "AREI-4.4.3-KRACHT" not in residential
    assert "AREI-4.4.3-KRACHT" in industrial


# ---------------------------------------------------------------------------
# disable / enable
# ---------------------------------------------------------------------------


def test_disable_enable_rule():
    syms = [_sym(SymbolType.WANDCONTACTDOOS, circuit="G1") for _ in range(9)]
    p_before = validate(_project(*syms))
    assert "AREI-4.4.2-WCD" in _codes(p_before)

    disable_rule("AREI-4.4.2-WCD")
    p_disabled = validate(_project(*syms))
    assert "AREI-4.4.2-WCD" not in _codes(p_disabled)

    enable_rule("AREI-4.4.2-WCD")
    p_after = validate(_project(*syms))
    assert "AREI-4.4.2-WCD" in _codes(p_after)


def test_disable_unknown_rule_raises():
    with pytest.raises(KeyError):
        disable_rule("BESTAAT-NIET")


# ---------------------------------------------------------------------------
# AREI Art. 4 — groepsleidingen
# ---------------------------------------------------------------------------


def test_arei_4_wcd_under_limit():
    syms = [_sym(SymbolType.WANDCONTACTDOOS, circuit="G1") for _ in range(8)]
    p = validate(_project(*syms))
    assert "AREI-4.4.2-WCD" not in _codes(p)


def test_arei_4_wcd_over_limit():
    syms = [_sym(SymbolType.WANDCONTACTDOOS, circuit="G1") for _ in range(9)]
    p = validate(_project(*syms))
    assert "AREI-4.4.2-WCD" in _codes(p)


def test_arei_4_licht_over_limit():
    syms = [_sym(SymbolType.LICHTPUNT, circuit="L1") for _ in range(13)]
    p = validate(_project(*syms))
    assert "AREI-4.4.2-LICHT" in _codes(p)


def test_arei_4_kracht_only_for_industrial_scope():
    """Krachtstopcontacten-regel mag niet vuren bij residentiële scope."""
    syms = [
        _sym(SymbolType.WANDCONTACTDOOS, circuit="K1", kracht=True)
        for _ in range(5)
    ]
    p_res = validate(_project(*syms), scope="residential")
    assert "AREI-4.4.3-KRACHT" not in _codes(p_res)

    p_ind = validate(_project(*syms), scope="industrial")
    assert "AREI-4.4.3-KRACHT" in _codes(p_ind)


def test_arei_4_lege_groep():
    syms = [_sym(SymbolType.VERDELER, circuit="H1")]
    p = validate(_project(*syms))
    assert "AREI-4-GROEP-LEEG" in _codes(p)


def test_arei_4_ongegroepeerd():
    syms = [_sym(SymbolType.WANDCONTACTDOOS)]  # geen circuit
    p = validate(_project(*syms))
    assert "AREI-4-ONGEGROEP" in _codes(p)


# ---------------------------------------------------------------------------
# AREI Art. 6 — beveiliging
# ---------------------------------------------------------------------------


def test_arei_6_ddr_warning_no_panel():
    syms = [_sym(SymbolType.LICHTPUNT, circuit="L1")]
    p = validate(_project(*syms), scope="residential")
    assert "AREI-6.4.1-DDR" in _codes(p)


def test_arei_6_ddr_no_warning_with_panel():
    syms = [
        _sym(SymbolType.LICHTPUNT, circuit="L1"),
        _sym(SymbolType.GROEPENKAST),
    ]
    p = validate(_project(*syms), scope="residential")
    assert "AREI-6.4.1-DDR" not in _codes(p)


def test_arei_6_ddr_suppressed_when_disabled_in_config():
    cfg = RulesConfig(safety=SafetyLimits(rcd_required=False))
    syms = [_sym(SymbolType.LICHTPUNT, circuit="L1")]
    p = validate(_project(*syms), config=cfg, scope="residential")
    assert "AREI-6.4.1-DDR" not in _codes(p)


def test_arei_6_panel_verplicht_boven_drempel():
    syms = [_sym(SymbolType.WANDCONTACTDOOS, circuit=f"G{i}") for i in range(1, 5)]
    p = validate(_project(*syms))
    assert "AREI-6.4.1-PANEL" in _codes(p)


# ---------------------------------------------------------------------------
# AREI Art. 7 / brandbeveiliging
# ---------------------------------------------------------------------------


def test_arei_7_rookmelder_aanwezig():
    room = _room("Slaapkamer kind")
    sym = _sym(SymbolType.ROOKMELDER, room_id=room.id)
    p = validate(_project(sym, rooms=[room]), scope="residential")
    assert "AREI-7-ROOK-SLAAP" not in _codes(p)


def test_arei_7_rookmelder_ontbreekt():
    room = _room("Slaapkamer ouders")
    p = validate(_project(rooms=[room]), scope="residential")
    assert "AREI-7-ROOK-SLAAP" in _codes(p)


def test_arei_7_rookmelder_niet_residentieel():
    """Rookmelderregel geldt alleen voor residential scope."""
    room = _room("Slaapkamer")
    p = validate(_project(rooms=[room]), scope="industrial")
    assert "AREI-7-ROOK-SLAAP" not in _codes(p)


def test_arei_7_noodverlichting_ontbreekt():
    room = _room("Gang begane grond")
    p = validate(_project(rooms=[room]))
    assert "AREI-7-NOOD-GANG" in _codes(p)


def test_arei_7_dubbel_symbool():
    syms = [
        _sym(SymbolType.WANDCONTACTDOOS, x=100.0, y=100.0),
        _sym(SymbolType.WANDCONTACTDOOS, x=100.0, y=115.0),  # 15 mm
    ]
    p = validate(_project(*syms))
    assert "AREI-7-DUBBEL" in _codes(p)


def test_arei_7_geen_dubbel_ver_uit_elkaar():
    syms = [
        _sym(SymbolType.WANDCONTACTDOOS, x=0.0, y=0.0),
        _sym(SymbolType.WANDCONTACTDOOS, x=1000.0, y=0.0),
    ]
    p = validate(_project(*syms))
    assert "AREI-7-DUBBEL" not in _codes(p)


# ---------------------------------------------------------------------------
# Projectniveau
# ---------------------------------------------------------------------------


def test_schema_panel_groot():
    syms = [_sym(SymbolType.WANDCONTACTDOOS) for _ in range(10)]
    p = validate(_project(*syms))
    assert "SCHEMA-PANEL-GROOT" in _codes(p)


def test_schema_panel_niet_nodig_klein():
    syms = [_sym(SymbolType.WANDCONTACTDOOS) for _ in range(5)]
    p = validate(_project(*syms))
    assert "SCHEMA-PANEL-GROOT" not in _codes(p)


def test_schema_onbekende_symbolen():
    syms = [_sym(SymbolType.ONBEKEND)]
    p = validate(_project(*syms))
    assert "SCHEMA-SYM-ONBEKEND" in _codes(p)


# ---------------------------------------------------------------------------
# Config-overschrijvingen
# ---------------------------------------------------------------------------


def test_custom_config_wcd_limit(monkeypatch):
    from dataclasses import replace
    cfg = replace(DEFAULT_CONFIG, circuit=CircuitLimits(max_wcd=3))
    syms = [_sym(SymbolType.WANDCONTACTDOOS, circuit="G1") for _ in range(4)]
    p = validate(_project(*syms), config=cfg)
    assert "AREI-4.4.2-WCD" in _codes(p)


def test_industrial_config_higher_limit():
    # INDUSTRIAL_CONFIG heeft max_wcd=16
    syms = [_sym(SymbolType.WANDCONTACTDOOS, circuit="G1") for _ in range(10)]
    p = validate(_project(*syms), config=INDUSTRIAL_CONFIG, scope="industrial")
    assert "AREI-4.4.2-WCD" not in _codes(p)


# ---------------------------------------------------------------------------
# Leeg project
# ---------------------------------------------------------------------------


def test_empty_project_no_warnings():
    p = validate(Project())
    assert p.warnings == []
