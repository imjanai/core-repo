"""
packages/rules/rules/arei_art7.py
AREI Art. 7 / NBN S21-208 — Brandbeveiliging en rookmelders.

Gedekte regels
--------------
AREI-7-ROOK-SLAAP   Rookmelder per slaapkamer verplicht
AREI-7-NOOD-GANG    Noodverlichting in vluchtroutes verplicht
AREI-7-DUBBEL       Dubbele symbolen op vrijwel dezelfde positie
"""

from __future__ import annotations

import math

from packages.rules.engine import rule
from packages.rules.limits import RulesConfig
from packages.schema import Project, Room, SymbolType, ValidationWarning


def _rooms_matching(rooms: list[Room], keywords: tuple[str, ...]) -> list[Room]:
    return [r for r in rooms if any(kw in r.name.lower() for kw in keywords)]


@rule(
    id="AREI-7-ROOK-SLAAP",
    description="Rookmelder verplicht in elke slaapkamer (NBN S21-208)",
    article="AREI Art. 7 / NBN S21-208:2013",
    source="NBN S21-208:2013",
    applies_to={"residential"},
)
def rookmelder_per_slaapkamer(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    NBN S21-208:2013 (Belgische brandveiligheidsnorm voor woningen):
    'In elke slaapkamer moet een optische rookmelder aanwezig zijn.'
    """
    if not cfg.fire.detector_per_bedroom:
        return []

    slaapkamers = _rooms_matching(p.rooms, cfg.fire.bedroom_keywords)
    if not slaapkamers:
        return []

    rooms_with_detector = {
        s.room_id for s in p.symbols
        if s.type == SymbolType.ROOKMELDER and s.room_id
    }
    warnings = []
    for room in slaapkamers:
        if room.id not in rooms_with_detector:
            warnings.append(ValidationWarning(
                code="AREI-7-ROOK-SLAAP",
                severity="warning",
                message=(
                    f"Geen rookmelder in '{room.name}' "
                    f"(NBN S21-208 — verplicht per slaapkamer)."
                ),
                symbol_ids=[],
            ))
    return warnings


@rule(
    id="AREI-7-NOOD-GANG",
    description="Noodverlichting verplicht in vluchtroutes en gangen",
    article="AREI Art. 7 / NEN-EN 1838",
    source="AREI 2023 / NEN-EN 1838:2013",
    applies_to={"residential", "commercial", "industrial"},
)
def noodverlichting_vluchtroute(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    AREI Art. 7 / NEN-EN 1838:
    'Vluchtroutes moeten voorzien zijn van noodverlichting die bij
    stroomuitval automatisch inschakelt.'
    """
    vluchtroutes = _rooms_matching(p.rooms, cfg.fire.escape_route_keywords)
    if not vluchtroutes:
        return []

    rooms_with_nood = {
        s.room_id for s in p.symbols
        if s.type == SymbolType.NOODVERLICHTING and s.room_id
    }
    warnings = []
    for room in vluchtroutes:
        if room.id not in rooms_with_nood:
            warnings.append(ValidationWarning(
                code="AREI-7-NOOD-GANG",
                severity="warning",
                message=(
                    f"Geen noodverlichting in vluchtroute '{room.name}' "
                    f"(AREI Art. 7 / NEN-EN 1838)."
                ),
                symbol_ids=[],
            ))
    return warnings


@rule(
    id="AREI-7-DUBBEL",
    description="Dubbele symbolen op vrijwel dezelfde positie (mogelijke tekenfout)",
    article="AREI Art. 7",
    source="AREI 2023",
    severity="warning",
    applies_to={"all"},
)
def dubbele_symbolen(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    Twee symbolen van hetzelfde type binnen `duplicate_distance_mm` van
    elkaar zijn vrijwel zeker import-duplicaten of tekenaarsfouten.
    """
    threshold = cfg.geometry.duplicate_distance_mm
    from collections import defaultdict
    by_type: dict[SymbolType, list] = defaultdict(list)
    for s in p.symbols:
        by_type[s.type].append(s)

    warnings = []
    for sym_type, syms in by_type.items():
        for i, a in enumerate(syms):
            for b in syms[i + 1:]:
                dist = math.hypot(a.x - b.x, a.y - b.y)
                if dist < threshold:
                    warnings.append(ValidationWarning(
                        code="AREI-7-DUBBEL",
                        severity="warning",
                        message=(
                            f"Mogelijk dubbel symbool '{sym_type.value}': "
                            f"{dist:.1f} mm van elkaar "
                            f"({a.x:.0f},{a.y:.0f}) ↔ ({b.x:.0f},{b.y:.0f})."
                        ),
                        symbol_ids=[a.id, b.id],
                    ))
    return warnings
