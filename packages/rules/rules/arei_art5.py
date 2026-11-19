"""
packages/rules/rules/arei_art5.py
AREI Art. 5 — Minimale uitrusting per ruimte.

Gedekte regels
--------------
AREI-5-WCD-SLAAP     Min. 2 WCD's per slaapkamer
AREI-5-WCD-WOON      Min. 4 WCD's per woonkamer / leefruimte
AREI-5-WCD-KEUKEN    Min. 6 WCD's in de keuken (AREI Art. 5 keuken)
AREI-5-SCHAKELAAR    Elke verlichte ruimte heeft een schakelaar
AREI-5-LICHT-KAMER   Elke kamer heeft minstens één lichtpunt
"""

from __future__ import annotations

from collections import defaultdict

from packages.rules.engine import rule
from packages.rules.limits import RulesConfig
from packages.schema import Project, Room, SymbolType, ValidationWarning

_WCD_TYPES = {SymbolType.WANDCONTACTDOOS, SymbolType.WANDCONTACTDOOS_DUBBEL}
_SCHAKELAAR_TYPES = {
    SymbolType.SCHAKELAAR, SymbolType.SCHAKELAAR_WISSEL,
    SymbolType.SCHAKELAAR_KRUIS, SymbolType.SCHAKELAAR_DIMMER,
    SymbolType.BEWEGINGSMELDER,
}
_LICHT_TYPES = {
    SymbolType.LICHTPUNT, SymbolType.LICHTPUNT_SPOT,
    SymbolType.LICHTPUNT_TL, SymbolType.LICHTPUNT_BUITEN,
}


def _count_in_room(p: Project, room_id: str, types: set[SymbolType]) -> int:
    return sum(1 for s in p.symbols if s.room_id == room_id and s.type in types)


def _wcd_count(p: Project, room_id: str) -> int:
    """Dubbele WCD telt als 2."""
    count = 0
    for s in p.symbols:
        if s.room_id != room_id:
            continue
        if s.type == SymbolType.WANDCONTACTDOOS:
            count += 1
        elif s.type == SymbolType.WANDCONTACTDOOS_DUBBEL:
            count += 2
    return count


def _rooms_matching(rooms: list[Room], keywords: tuple[str, ...]) -> list[Room]:
    return [r for r in rooms if any(kw in r.name.lower() for kw in keywords)]


@rule(
    id="AREI-5-WCD-SLAAP",
    description="Minimaal 2 wandcontactdozen per slaapkamer (AREI Art. 5)",
    article="AREI Art. 5",
    source="AREI 2023",
    applies_to={"residential"},
)
def min_wcd_slaapkamer(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    AREI Art. 5 (editie 2023):
    'In elke slaapkamer moeten minimaal 2 geaarde contactdozen aanwezig zijn.'
    """
    slaapkamers = _rooms_matching(p.rooms, cfg.fire.bedroom_keywords)
    minimum = cfg.circuit.min_wcd_per_room
    warnings = []
    for room in slaapkamers:
        n = _wcd_count(p, room.id)
        if n < minimum:
            warnings.append(ValidationWarning(
                code="AREI-5-WCD-SLAAP",
                severity="warning",
                message=(
                    f"'{room.name}': {n} WCD(s) gevonden, "
                    f"minimum {minimum} vereist (AREI Art. 5)."
                ),
                symbol_ids=[
                    s.id for s in p.symbols
                    if s.room_id == room.id and s.type in _WCD_TYPES
                ],
            ))
    return warnings


@rule(
    id="AREI-5-WCD-WOON",
    description="Minimaal 4 wandcontactdozen in woonkamer/leefruimte",
    article="AREI Art. 5",
    source="AREI 2023",
    applies_to={"residential"},
)
def min_wcd_woonkamer(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    woon_keywords = ("woon", "living", "séjour", "salon", "leef")
    kamers = _rooms_matching(p.rooms, woon_keywords)
    minimum = cfg.project.min_wcd_woonkamer
    warnings = []
    for room in kamers:
        n = _wcd_count(p, room.id)
        if n < minimum:
            warnings.append(ValidationWarning(
                code="AREI-5-WCD-WOON",
                severity="warning",
                message=(
                    f"'{room.name}': {n} WCD(s), minimum {minimum} "
                    f"aanbevolen in leefruimte (AREI Art. 5)."
                ),
                symbol_ids=[
                    s.id for s in p.symbols
                    if s.room_id == room.id and s.type in _WCD_TYPES
                ],
            ))
    return warnings


@rule(
    id="AREI-5-WCD-KEUKEN",
    description="Minimaal 6 wandcontactdozen boven het aanrecht (AREI Art. 5)",
    article="AREI Art. 5",
    source="AREI 2023",
    applies_to={"residential"},
)
def min_wcd_keuken(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    AREI Art. 5 — keuken:
    'Boven het werkvlak moeten minstens 6 geaarde contactdozen aanwezig zijn.'
    """
    keuken_keywords = ("keuken", "cuisine", "kitchen", "cuisi")
    keukens = _rooms_matching(p.rooms, keuken_keywords)
    minimum = cfg.project.min_wcd_keuken
    warnings = []
    for room in keukens:
        n = _wcd_count(p, room.id)
        if n < minimum:
            warnings.append(ValidationWarning(
                code="AREI-5-WCD-KEUKEN",
                severity="warning",
                message=(
                    f"'{room.name}': {n} WCD(s), minimum {minimum} "
                    f"boven het werkvlak vereist (AREI Art. 5)."
                ),
                symbol_ids=[
                    s.id for s in p.symbols
                    if s.room_id == room.id and s.type in _WCD_TYPES
                ],
            ))
    return warnings


@rule(
    id="AREI-5-SCHAKELAAR",
    description="Elke verlichte ruimte heeft een schakelaar of bewegingsmelder",
    article="AREI Art. 5",
    source="AREI 2023",
    severity="info",
    applies_to={"residential", "commercial"},
)
def schakelaar_per_verlichte_kamer(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """Ruimte met lichtpunt maar zonder schakelaar/bewegingsmelder → info."""
    if not p.rooms:
        return []
    warnings = []
    for room in p.rooms:
        heeft_licht = _count_in_room(p, room.id, _LICHT_TYPES) > 0
        heeft_schakelaar = _count_in_room(p, room.id, _SCHAKELAAR_TYPES) > 0
        if heeft_licht and not heeft_schakelaar:
            warnings.append(ValidationWarning(
                code="AREI-5-SCHAKELAAR",
                severity="info",
                message=(
                    f"'{room.name}': lichtpunt zonder schakelaar of bewegingsmelder."
                ),
                symbol_ids=[
                    s.id for s in p.symbols
                    if s.room_id == room.id and s.type in _LICHT_TYPES
                ],
            ))
    return warnings


@rule(
    id="AREI-5-LICHT-KAMER",
    description="Elke ruimte heeft minstens één lichtpunt",
    article="AREI Art. 5",
    source="AREI 2023",
    severity="info",
    applies_to={"residential"},
)
def licht_per_kamer(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    if not p.rooms:
        return []
    _ALLE_LICHT = _LICHT_TYPES | {SymbolType.NOODVERLICHTING}
    warnings = []
    for room in p.rooms:
        if _count_in_room(p, room.id, _ALLE_LICHT) == 0:
            warnings.append(ValidationWarning(
                code="AREI-5-LICHT-KAMER",
                severity="info",
                message=f"'{room.name}': geen lichtpunt ingetekend.",
                symbol_ids=[],
            ))
    return warnings
