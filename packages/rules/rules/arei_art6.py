"""
packages/rules/rules/arei_art6.py
AREI Art. 6 — Beveiliging tegen elektrische schokken / aardlekbeveiliging.

Gedekte regels
--------------
AREI-6.4.1-DDR     Aardlekschakelaar verplicht in woningen
AREI-6.4.1-PANEL   Groepenkast ontbreekt bij meerdere groepen
AREI-6-GRP-BEVEIL  Groepen zonder zichtbaar beveiligingsapparaat
"""

from __future__ import annotations

import math

from packages.rules.engine import rule
from packages.rules.limits import RulesConfig
from packages.schema import Project, SymbolType, ValidationWarning

_PANEL_TYPES = {SymbolType.VERDELER, SymbolType.GROEPENKAST}
_LOAD_TYPES = {SymbolType.WANDCONTACTDOOS, SymbolType.LICHTPUNT}


@rule(
    id="AREI-6.4.1-DDR",
    description="Aardlekschakelaar (DDR) verplicht in woningen (AREI Art. 6.4.1)",
    article="AREI Art. 6.4.1",
    source="AREI 2023",
    applies_to={"residential"},
)
def aardlekschakelaar_verplicht(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    AREI Art. 6.4.1 (editie 2023):
    'In woongelegenheden moet elke groepsleiding die contactdozen of
    verlichtingspunten voedt, beveiligd worden door een differentiaalschakelaar
    met een nominale differentiaalstroom van ten hoogste 30 mA.'

    We controleren hier of er circuits met belasting zijn maar geen verdeler/kast
    ingetekend — dat is de sterkste beschikbare proxy zonder schakelschema.
    """
    if not cfg.safety.rcd_required:
        return []

    circuits_with_load = {
        s.circuit for s in p.symbols
        if s.circuit and s.type in _LOAD_TYPES
    }
    if not circuits_with_load:
        return []

    has_panel = any(s.type in _PANEL_TYPES for s in p.symbols)
    if has_panel:
        return []

    n = len(circuits_with_load)
    return [ValidationWarning(
        code="AREI-6.4.1-DDR",
        severity="warning",
        message=(
            f"{n} groep(en) met belasting maar geen verdeler/groepenkast "
            f"ingetekend — aardlekbeveiliging ≤{cfg.safety.rcd_max_ma} mA "
            f"verplicht (AREI Art. 6.4.1)."
        ),
        symbol_ids=[],
    )]


@rule(
    id="AREI-6.4.1-PANEL",
    description="Groepenkast ontbreekt bij meerdere circuits",
    article="AREI Art. 6.4.1",
    source="AREI 2023",
    applies_to={"all"},
)
def groepenkast_verplicht(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    circuits = {s.circuit for s in p.symbols if s.circuit}
    if len(circuits) < cfg.project.min_circuits_for_kast:
        return []

    has_panel = any(s.type in _PANEL_TYPES for s in p.symbols)
    if has_panel:
        return []

    return [ValidationWarning(
        code="AREI-6.4.1-PANEL",
        severity="warning",
        message=(
            f"{len(circuits)} circuits aanwezig maar geen verdeler/groepenkast "
            f"ingetekend — voeg een groepenkast toe aan het schema."
        ),
        symbol_ids=[],
    )]


@rule(
    id="AREI-6-GRP-BEVEIL",
    description="Groepen aanwezig maar geen beveiliging ingetekend",
    article="AREI Art. 6",
    source="AREI 2023",
    severity="info",
    applies_to={"all"},
)
def groep_zonder_beveiliging(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    circuits = {s.circuit for s in p.symbols if s.circuit}
    if not circuits:
        return []
    has_panel = any(s.type in _PANEL_TYPES for s in p.symbols)
    if has_panel:
        return []
    return [ValidationWarning(
        code="AREI-6-GRP-BEVEIL",
        severity="info",
        message=(
            f"{len(circuits)} groep(en) gevonden maar geen verdeler/groepenkast — "
            f"controleer of beveiliging aanwezig is (AREI Art. 6)."
        ),
        symbol_ids=[],
    )]
