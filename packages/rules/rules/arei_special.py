"""
packages/rules/rules/arei_special.py
AREI — Speciale installaties: EV-laden, PV, CO-detectie, natte lokalen,
       potentiaalvereffening, overspanningsbeveiliging.

Gedekte regels
--------------
AREI-SPEC-EV-RCD     EV-laadpunt vereist eigen type-B aardlekautomaat
AREI-SPEC-PV-HOOFD   PV-installatie vereist eigen hoofdschakelaar/beveiliging
AREI-SPEC-CO-STOOK   CO-melder verplicht in stookruimte/garage
AREI-SPEC-SPD        Overspanningsbeveiliging bij grote installaties
AREI-SPEC-EQUIP      Potentiaalvereffening verplicht in natte lokalen
AREI-SPEC-IP-BAD     IP44-minimum in badkamer zone 2
"""

from __future__ import annotations

from packages.rules.engine import rule
from packages.rules.limits import RulesConfig
from packages.schema import Project, Room, SymbolType, ValidationWarning


def _rooms_matching(rooms: list[Room], keywords: tuple[str, ...]) -> list[Room]:
    return [r for r in rooms if any(kw in r.name.lower() for kw in keywords)]


_WET_ROOM_KEYWORDS = ("bad", "douche", "wc", "toilet", "sanitair",
                       "salle de bain", "douche", "lavabo")
_BOILER_KEYWORDS = ("stook", "ketel", "garage", "chaufferie", "boiler", "technisch")


@rule(
    id="AREI-SPEC-EV-RCD",
    description="EV-laadpunt vereist eigen type-B aardlekautomaat (AREI)",
    article="AREI Art. 7 / IEC 61851",
    source="AREI 2023 / IEC 61851-1",
    applies_to={"residential", "commercial"},
)
def ev_laadpaal_beveiliging(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    AREI Art. 7 / IEC 61851:
    'Een EV-laadpunt moet beveiligd worden door een aardlekautomaat type B
    of een gelijkwaardige combinatie (type A + DC-lekstroomdetectie).'
    """
    if not cfg.special.ev_requires_type_b_rcd:
        return []
    ev_syms = [s for s in p.symbols if s.type == SymbolType.LAADPAAL]
    if not ev_syms:
        return []

    # Controleer of er een aardlekautomaat of aardlekschakelaar aanwezig is
    has_rcbo = any(
        s.type in {SymbolType.AARDLEKAUTOMAAT, SymbolType.AARDLEKSCHAKELAAR}
        for s in p.symbols
    )
    if has_rcbo:
        return []

    return [ValidationWarning(
        code="AREI-SPEC-EV-RCD",
        severity="error",
        message=(
            f"{len(ev_syms)} EV-laadpunt(en) aanwezig zonder aardlekautomaat "
            f"type B — verplicht per AREI Art. 7 / IEC 61851."
        ),
        symbol_ids=[s.id for s in ev_syms],
    )]


@rule(
    id="AREI-SPEC-PV-HOOFD",
    description="PV-installatie vereist eigen beveiligings-/hoofdschakelaar",
    article="AREI Art. 7 / Synergrid C10/11",
    source="AREI 2023 / Synergrid C10/11",
    applies_to={"residential", "commercial", "industrial"},
)
def pv_beveiliging(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    Synergrid C10/11 (Belgisch net-aansluitreglement):
    'Bij een PV-installatie moet een terugleverbeveiliging aanwezig zijn
    en de installatie moet voorzien zijn van een zichtbare scheidingsschakelaar.'
    """
    pv_syms = [s for s in p.symbols if s.type == SymbolType.ZONNEPANEEL_OMVORMER]
    if not pv_syms:
        return []

    has_main_switch = any(
        s.type == SymbolType.HOOFDSCHAKELAAR for s in p.symbols
    )
    if has_main_switch:
        return []

    return [ValidationWarning(
        code="AREI-SPEC-PV-HOOFD",
        severity="warning",
        message=(
            f"{len(pv_syms)} PV-omvormer(s) aanwezig zonder zichtbare "
            f"hoofdschakelaar — vereist per Synergrid C10/11."
        ),
        symbol_ids=[s.id for s in pv_syms],
    )]


@rule(
    id="AREI-SPEC-CO-STOOK",
    description="CO-melder verplicht in stookruimte en garage (AREI / RGBSR)",
    article="AREI Art. 7 / RGBSR",
    source="AREI 2023 / RGBSR",
    applies_to={"residential"},
)
def co_melder_stookruimte(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    AREI / RGBSR (Belgisch stooktorenreglement):
    'In elke ruimte met een verbrandingstoestel of garage moet een
    koolmonoxidemelder aanwezig zijn.'
    """
    if not cfg.fire.co_detector_in_boilerroom:
        return []

    stookruimtes = _rooms_matching(p.rooms, _BOILER_KEYWORDS)
    if not stookruimtes:
        return []

    rooms_with_co = {
        s.room_id for s in p.symbols
        if s.type == SymbolType.KOOLMONOXIDEMELDER and s.room_id
    }
    warnings = []
    for room in stookruimtes:
        if room.id not in rooms_with_co:
            warnings.append(ValidationWarning(
                code="AREI-SPEC-CO-STOOK",
                severity="warning",
                message=(
                    f"Geen CO-melder in '{room.name}' "
                    f"(AREI / RGBSR — verplicht bij verbrandingstoestel/garage)."
                ),
                symbol_ids=[],
            ))
    return warnings


@rule(
    id="AREI-SPEC-SPD",
    description="Overspanningsbeveiliging (SPD) bij installaties boven de drempel",
    article="AREI Art. 6 / IEC 60364-4-44",
    source="AREI 2023 / IEC 60364-4-44",
    applies_to={"residential", "commercial", "industrial"},
)
def overspanningsbeveiliging(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    IEC 60364-4-44 / AREI Art. 6:
    'Bij installaties met gevoelige apparatuur of boven bepaalde waarden
    is een SPD type 2 verplicht op de hoofdverdeelkast.'
    """
    # Proxy: aanwezig als er een PV-omvormer, laadpaal of accu is
    sensitive = [
        s for s in p.symbols
        if s.type in {
            SymbolType.ZONNEPANEEL_OMVORMER,
            SymbolType.ACCU_OPSLAG,
            SymbolType.LAADPAAL,
        }
    ]
    if not sensitive:
        return []

    has_spd = any(
        s.type == SymbolType.OVERSPANNINGSBEVEILIGING for s in p.symbols
    )
    if has_spd:
        return []

    return [ValidationWarning(
        code="AREI-SPEC-SPD",
        severity="warning",
        message=(
            "Gevoelige installaties (PV/EV/accu) aanwezig maar geen "
            "overspanningsbeveiliging SPD — aanbevolen per IEC 60364-4-44."
        ),
        symbol_ids=[s.id for s in sensitive],
    )]


@rule(
    id="AREI-SPEC-EQUIP",
    description="Potentiaalvereffening verplicht in natte lokalen (AREI Art. 6)",
    article="AREI Art. 6.3",
    source="AREI 2023",
    applies_to={"residential", "commercial"},
)
def potentiaalvereffening_nat_lokaal(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    AREI Art. 6.3:
    'In badkamers en andere natte lokalen moet een lokale
    aanvullende potentiaalvereffening aanwezig zijn.'
    """
    if not cfg.safety.equipotential_in_wet_room:
        return []

    natte_lokalen = _rooms_matching(p.rooms, _WET_ROOM_KEYWORDS)
    if not natte_lokalen:
        return []

    rooms_with_equip = {
        s.room_id for s in p.symbols
        if s.type == SymbolType.POTENTIAALVEREFFENINGSPUNT and s.room_id
    }
    warnings = []
    for room in natte_lokalen:
        if room.id not in rooms_with_equip:
            warnings.append(ValidationWarning(
                code="AREI-SPEC-EQUIP",
                severity="warning",
                message=(
                    f"Geen potentiaalvereffeningspunt in '{room.name}' "
                    f"(AREI Art. 6.3 — verplicht in nat lokaal)."
                ),
                symbol_ids=[],
            ))
    return warnings


@rule(
    id="AREI-SPEC-IP-BAD",
    description="Contactdozen in badkamer minimum IP44 (AREI Art. 6)",
    article="AREI Art. 6 / IEC 60364-7-701",
    source="AREI 2023 / IEC 60364-7-701",
    applies_to={"residential", "commercial"},
)
def ip_badkamer(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    IEC 60364-7-701 / AREI:
    'Contactdozen in badkamer zone 2 en buiten moeten minimaal IP44 zijn.'
    Proxy: contactdoos in ruimte met badkamer-keywords maar geen
    waterdicht type → waarschuwing.
    """
    badkamers = _rooms_matching(p.rooms, ("bad", "douche", "salle de bain"))
    if not badkamers:
        return []

    warnings = []
    for room in badkamers:
        gewone_wcd = [
            s for s in p.symbols
            if s.room_id == room.id
            and s.type == SymbolType.WANDCONTACTDOOS  # niet waterdicht
        ]
        if gewone_wcd:
            warnings.append(ValidationWarning(
                code="AREI-SPEC-IP-BAD",
                severity="error",
                message=(
                    f"'{room.name}': {len(gewone_wcd)} standaard WCD(s) — "
                    f"gebruik IP44/IP55 uitvoering (AREI / IEC 60364-7-701)."
                ),
                symbol_ids=[s.id for s in gewone_wcd],
            ))
    return warnings
