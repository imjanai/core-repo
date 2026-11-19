"""
packages/rules/rules/arei_domotica.py
Domotica & communicatie-installaties — deurbel, intercom, data, toegang.

Gedekte regels
--------------
DOM-BEL-DRUKKER   Deurbeldrukker aanwezig maar geen belinstallatie (of omgekeerd)
DOM-DATA-MINSTENS Minimaal één datapunt per woon-/werk-ruimte (advies)
DOM-INTERCOM-CAM  Videofoon aanwezig maar geen intercom/buitenunit (consistentie)
DOM-TOEGANG-NOOD  Toegangslezer aanwezig maar geen UPS / noodvoeding
"""

from __future__ import annotations

from packages.rules.engine import rule
from packages.rules.limits import RulesConfig
from packages.schema import Project, Room, SymbolType, ValidationWarning


def _rooms_matching(rooms: list[Room], keywords: tuple[str, ...]) -> list[Room]:
    return [r for r in rooms if any(kw in r.name.lower() for kw in keywords)]


@rule(
    id="DOM-BEL-DRUKKER",
    description="Deurbeldrukker aanwezig maar geen belinstallatie (consistentie)",
    article="—",
    source="imJan AI intern",
    severity="info",
    applies_to={"residential", "commercial"},
)
def deurbel_consistentie(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    Als er een deurbeldrukker ingetekend staat maar geen deurbelinstallatie,
    ontbreekt er mogelijk een component.  Omgekeerd ook.
    """
    has_drukker = any(s.type == SymbolType.DEURBELDRUKKER for s in p.symbols)
    has_installatie = any(
        s.type in {SymbolType.DEURBELINSTALLATIE, SymbolType.INTERCOM, SymbolType.VIDEOFOON}
        for s in p.symbols
    )
    warnings = []
    if has_drukker and not has_installatie:
        warnings.append(ValidationWarning(
            code="DOM-BEL-DRUKKER",
            severity="info",
            message=(
                "Deurbeldrukker aanwezig maar geen deurbelinstallatie, "
                "intercom of videofoon — controleer schema."
            ),
            symbol_ids=[s.id for s in p.symbols if s.type == SymbolType.DEURBELDRUKKER],
        ))
    if has_installatie and not has_drukker:
        warnings.append(ValidationWarning(
            code="DOM-BEL-DRUKKER",
            severity="info",
            message=(
                "Deurbelinstallatie/intercom aanwezig maar geen deurbeldrukker — "
                "buitenunit ontbreekt mogelijk."
            ),
            symbol_ids=[
                s.id for s in p.symbols
                if s.type in {SymbolType.DEURBELINSTALLATIE, SymbolType.INTERCOM, SymbolType.VIDEOFOON}
            ],
        ))
    return warnings


@rule(
    id="DOM-DATA-MINSTENS",
    description="Minimaal één datapunt per leefruimte (advies NEN 1010 / AREI)",
    article="AREI Art. 5",
    source="AREI 2023",
    severity="info",
    applies_to={"residential", "commercial"},
)
def datapunt_per_leefruimte(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    if not p.rooms:
        return []
    leef_keywords = ("woon", "living", "bureau", "office", "studie", "séjour", "salon")
    leefruimtes = _rooms_matching(p.rooms, leef_keywords)
    _DATA_TYPES = {SymbolType.DATAPUNT, SymbolType.DATAPUNT_DUBBEL}
    warnings = []
    for room in leefruimtes:
        has_data = any(
            s.room_id == room.id and s.type in _DATA_TYPES
            for s in p.symbols
        )
        if not has_data:
            warnings.append(ValidationWarning(
                code="DOM-DATA-MINSTENS",
                severity="info",
                message=(
                    f"'{room.name}': geen datapunt aanwezig "
                    f"(aanbevolen voor bekabeld netwerk)."
                ),
                symbol_ids=[],
            ))
    return warnings


@rule(
    id="DOM-INTERCOM-CAM",
    description="Videofoon aanwezig maar geen intercom/buitenunit (consistentie)",
    article="—",
    source="imJan AI intern",
    severity="info",
    applies_to={"all"},
)
def videofoon_consistentie(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    has_video = any(s.type == SymbolType.VIDEOFOON for s in p.symbols)
    has_intercom = any(s.type == SymbolType.INTERCOM for s in p.symbols)
    if has_video and not has_intercom:
        return [ValidationWarning(
            code="DOM-INTERCOM-CAM",
            severity="info",
            message=(
                "Videofoon (binnenunit) aanwezig maar geen intercom buitenunit — "
                "buitencamera/spreekpost ontbreekt mogelijk."
            ),
            symbol_ids=[s.id for s in p.symbols if s.type == SymbolType.VIDEOFOON],
        )]
    return []


@rule(
    id="DOM-TOEGANG-NOOD",
    description="Toegangslezer zonder UPS — risico bij stroomuitval",
    article="AREI Art. 7",
    source="AREI 2023",
    severity="info",
    applies_to={"commercial", "industrial"},
)
def toegangslezer_noodvoeding(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    lezers = [s for s in p.symbols if s.type == SymbolType.TOEGANGSLEZER]
    if not lezers:
        return []
    has_ups = any(s.type == SymbolType.UPS for s in p.symbols)
    if has_ups:
        return []
    return [ValidationWarning(
        code="DOM-TOEGANG-NOOD",
        severity="info",
        message=(
            f"{len(lezers)} toegangslezer(s) zonder UPS — bij stroomuitval "
            f"kan toegang geblokkeerd zijn (overweeg noodvoeding)."
        ),
        symbol_ids=[s.id for s in lezers],
    )]
