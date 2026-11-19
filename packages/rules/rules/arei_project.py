"""
packages/rules/rules/arei_project.py
Installatieniveau-controles — geen specifiek AREI-artikel maar gang-bare
completenessregels die de kwaliteit van het schema bewaken.

Gedekte regels
--------------
SCHEMA-PANEL-GROOT   Verdeler verplicht bij grote installatie
SCHEMA-SYM-ONBEKEND  Onbekende symbolen aanwezig (confidentieproblemen)
"""

from __future__ import annotations

from packages.rules.engine import rule
from packages.rules.limits import RulesConfig
from packages.schema import Project, SymbolType, ValidationWarning

_PANEL_TYPES = {SymbolType.VERDELER, SymbolType.GROEPENKAST}


@rule(
    id="SCHEMA-PANEL-GROOT",
    description="Verdeler/groepenkast verplicht bij installaties boven de drempel",
    article="AREI Art. 4 / Art. 6 (projectniveau)",
    source="AREI 2023",
    applies_to={"all"},
)
def verdeler_vereist(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    if len(p.symbols) < cfg.project.min_symbols_for_panel:
        return []
    if any(s.type in _PANEL_TYPES for s in p.symbols):
        return []
    return [ValidationWarning(
        code="SCHEMA-PANEL-GROOT",
        severity="warning",
        message=(
            f"{len(p.symbols)} symbolen maar geen verdeler/groepenkast — "
            f"voeg een verdeelkast toe aan het schema (AREI Art. 4/6)."
        ),
        symbol_ids=[],
    )]


@rule(
    id="SCHEMA-SYM-ONBEKEND",
    description="Onbekende symbolen aanwezig (lage herkenningszekerheid)",
    article="—",
    source="imJan AI intern",
    severity="info",
    applies_to={"all"},
)
def onbekende_symbolen(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    Symbolen die het model niet kon herkennen (type=ONBEKEND).
    Ze worden niet meegenomen in de materiaallijst of regels.
    Een elektricien moet ze handmatig beoordelen.
    """
    unknown = [s for s in p.symbols if s.type == SymbolType.ONBEKEND]
    if not unknown:
        return []
    return [ValidationWarning(
        code="SCHEMA-SYM-ONBEKEND",
        severity="info",
        message=(
            f"{len(unknown)} onbekend(e) symbool/symbolen — "
            f"controleer en corrigeer via de review-UI."
        ),
        symbol_ids=[s.id for s in unknown],
    )]
