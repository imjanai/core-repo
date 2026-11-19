"""
packages/materials/engine.py — symbolen → materiaallijst.

Pipeline-stap 8 uit het README:
    Symbool → artikel → hoeveelheid → prijs

Aanpak:
1. Groepeer symbolen per (SymbolType, circuit, room_id) — symbolen van
   dezelfde soort in dezelfde groep/ruimte worden samengevoegd.
2. Zoek het catalogusartikel op voor elk symbooltype.
3. Bereken hoeveelheden en prijzen.
4. Voeg installatiebenodigdheden toe (kabels, buizen, inbouwdozen) op basis
   van vuistregels die in de elektrotechniek gangbaar zijn.
5. Geef een gesorteerde lijst van MaterialLine terug.

Alles is deterministisch en testbaar — geen LLM-aanroepen hier.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import NamedTuple

from packages.materials.catalogue import get_entry
from packages.schema import MaterialLine, Project, Symbol, SymbolType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Interne groepeersleutel
# ---------------------------------------------------------------------------


class _GroupKey(NamedTuple):
    symbol_type: SymbolType
    circuit: str  # "" als onbekend
    room_id: str  # "" als onbekend


# ---------------------------------------------------------------------------
# Vuistregels voor installatiebenodigdheden
# ---------------------------------------------------------------------------

# Hoeveel meter kabel (NYM-J 3×1.5) gemiddeld per symbool?
_CABLE_METER_PER_SYMBOL: dict[SymbolType, float] = {
    # Contactdozen & schakelaars
    SymbolType.WANDCONTACTDOOS: 4.0,
    SymbolType.WANDCONTACTDOOS_DUBBEL: 4.0,
    SymbolType.WANDCONTACTDOOS_WATERDICHT: 4.0,
    SymbolType.WANDCONTACTDOOS_KRACHT: 6.0,   # 2.5mm² krachtkabel
    SymbolType.SCHAKELAAR: 2.5,
    SymbolType.SCHAKELAAR_WISSEL: 3.0,        # 2 aders extra voor wisselschakeling
    SymbolType.SCHAKELAAR_KRUIS: 2.5,
    SymbolType.SCHAKELAAR_DIMMER: 2.5,
    SymbolType.SCHAKELAAR_TIJDSCHAKELAAR: 2.5,
    SymbolType.BEWEGINGSMELDER: 3.0,
    SymbolType.DRUKKNOP: 2.0,
    # Verlichting
    SymbolType.LICHTPUNT: 3.0,
    SymbolType.LICHTPUNT_SPOT: 3.0,
    SymbolType.LICHTPUNT_TL: 3.5,
    SymbolType.LICHTPUNT_BUITEN: 5.0,         # langere buitenroute
    SymbolType.NOODVERLICHTING: 3.0,
    SymbolType.NOODVERLICHTING_PICTOGRAM: 3.0,
    # Klimaat
    SymbolType.THERMOSTAAT: 2.0,
    SymbolType.VENTILATIEVENTIEL: 3.0,
    # Detectie / beveiliging
    SymbolType.ROOKMELDER: 2.0,
    SymbolType.KOOLMONOXIDEMELDER: 2.0,
    SymbolType.HITTEMELDER: 2.0,
    SymbolType.GASDETECTOR: 3.0,
    SymbolType.BEWEGINGSMELDER: 3.0,
    # Domotica
    SymbolType.DEURBELDRUKKER: 3.0,
    SymbolType.INTERCOM: 5.0,
    SymbolType.VIDEOFOON: 5.0,
}

# Data-symbolen krijgen UTP-kabel i.p.v. NYM-J
_DATA_SYMBOL_TYPES: set[SymbolType] = {
    SymbolType.DATAPUNT,
    SymbolType.DATAPUNT_DUBBEL,
    SymbolType.TELEFOONPUNT,
    SymbolType.TV_PUNT,
    SymbolType.AUDIO_PUNT,
    SymbolType.TOEGANGSLEZER,
}

# Symbolen waarvoor een inbouwdoos nodig is
_INBOUWDOOS_TYPES: set[SymbolType] = {
    SymbolType.WANDCONTACTDOOS,
    SymbolType.WANDCONTACTDOOS_DUBBEL,
    SymbolType.WANDCONTACTDOOS_WATERDICHT,
    SymbolType.SCHAKELAAR,
    SymbolType.SCHAKELAAR_WISSEL,
    SymbolType.SCHAKELAAR_KRUIS,
    SymbolType.SCHAKELAAR_DIMMER,
    SymbolType.SCHAKELAAR_TIJDSCHAKELAAR,
    SymbolType.LICHTPUNT,
    SymbolType.LICHTPUNT_SPOT,
    SymbolType.DATAPUNT,
    SymbolType.DATAPUNT_DUBBEL,
    SymbolType.THERMOSTAAT,
    SymbolType.DRUKKNOP,
    SymbolType.DEURBELDRUKKER,
}

# Catalogus-stubs voor installatiebenodigdheden (niet in catalogue.json
# omdat ze geen eigen symbool hebben).
_ANCILLARY_CATALOGUE = {
    "kabel_nym_j_3x15": {
        "etim_code": "EC000233",
        "description": "Installatiekabel NYM-J 3×1,5mm² grijs (p.m.)",
        "unit": "m",
        "unit_price": 1.05,
    },
    "kabel_utp_cat6": {
        "etim_code": "EC001489",
        "description": "UTP-kabel Cat.6 4×2×0,5 LSZH (p.m.)",
        "unit": "m",
        "unit_price": 0.65,
    },
    "inbouwdoos_enkel": {
        "etim_code": "EC000196",
        "description": "Inbouwdoos enkelvoudig ø60mm kunststof",
        "unit": "st",
        "unit_price": 0.45,
    },
    "zekering_b16": {
        "etim_code": "EC000189",
        "description": "Installatieautomaat B16A 1P+N 6kA",
        "unit": "st",
        "unit_price": 12.50,
    },
    "diff_30ma": {
        "etim_code": "EC000191",
        "description": "Aardlekschakelaar 40A 30mA 2P type-A",
        "unit": "st",
        "unit_price": 38.00,
    },
}


# ---------------------------------------------------------------------------
# Hoofd-engine
# ---------------------------------------------------------------------------


def compute_materials(project: Project) -> Project:
    """
    Verrijkt `project.materials` op basis van `project.symbols`.
    Geeft hetzelfde Project-object terug met een gevulde materials-lijst.
    """
    if not project.symbols:
        logger.warning("compute_materials: geen symbolen in project %s", project.id)
        project.materials = []
        return project

    lines: list[MaterialLine] = []

    # --- Stap 1: Groepeer symbolen ---
    groups: dict[_GroupKey, list[Symbol]] = defaultdict(list)
    for sym in project.symbols:
        key = _GroupKey(
            symbol_type=sym.type,
            circuit=sym.circuit or "",
            room_id=sym.room_id or "",
        )
        groups[key].append(sym)

    # --- Stap 2 & 3: Catalogus opzoeken + hoeveelheden/prijzen ---
    for key, symbols in groups.items():
        entry = get_entry(key.symbol_type.value)
        qty = len(symbols)
        unit_price = entry.get("unit_price")
        total_price = round(unit_price * qty, 2) if unit_price is not None else None

        lines.append(
            MaterialLine(
                symbol_id=symbols[0].id,  # representatief (eerste in groep)
                symbol_type=key.symbol_type,
                etim_code=entry.get("etim_code"),
                description=entry["description"],
                quantity=qty,
                unit=entry["unit"],
                unit_price=unit_price,
                total_price=total_price,
            )
        )

    # --- Stap 4: Installatiebenodigdheden ---
    lines.extend(_ancillary_lines(project.symbols))

    # --- Stap 5: Sortering (type alfabetisch, dan circuit) ---
    lines.sort(key=lambda l: (l.symbol_type.value, l.description))

    project.materials = lines
    logger.info(
        "compute_materials: %d regels gegenereerd voor project %s",
        len(lines),
        project.id,
    )
    return project


# ---------------------------------------------------------------------------
# Hulpfunctie: installatiebenodigdheden
# ---------------------------------------------------------------------------


def _ancillary_lines(symbols: list[Symbol]) -> list[MaterialLine]:
    """
    Berekent kabels, inbouwdozen en beveiligingscomponenten op basis van
    vuistregels. Alle regels krijgen een nep-symbol_id "ancillary".
    """
    lines: list[MaterialLine] = []

    # Scheid data-kabel van voedingskabel
    utp_symbols = [s for s in symbols if s.type in _DATA_SYMBOL_TYPES]
    nym_symbols = [
        s for s in symbols
        if s.type in _CABLE_METER_PER_SYMBOL and s.type not in _DATA_SYMBOL_TYPES
    ]

    nym_meter = round(
        sum(_CABLE_METER_PER_SYMBOL.get(s.type, 0.0) for s in nym_symbols), 1
    )
    utp_meter = round(
        sum(5.0 for s in utp_symbols), 1  # 5m gemiddeld per datapunt
    )

    if nym_meter > 0:
        cat = _ANCILLARY_CATALOGUE["kabel_nym_j_3x15"]
        lines.append(
            MaterialLine(
                symbol_id="ancillary",
                symbol_type=SymbolType.ONBEKEND,
                etim_code=cat["etim_code"],
                description=cat["description"],
                quantity=int(nym_meter),
                unit=cat["unit"],
                unit_price=cat["unit_price"],
                total_price=round(cat["unit_price"] * nym_meter, 2),
            )
        )

    if utp_meter > 0:
        cat = _ANCILLARY_CATALOGUE["kabel_utp_cat6"]
        lines.append(
            MaterialLine(
                symbol_id="ancillary",
                symbol_type=SymbolType.ONBEKEND,
                etim_code=cat["etim_code"],
                description=cat["description"],
                quantity=int(utp_meter),
                unit=cat["unit"],
                unit_price=cat["unit_price"],
                total_price=round(cat["unit_price"] * utp_meter, 2),
            )
        )

    # Inbouwdozen
    inbouw_count = sum(1 for s in symbols if s.type in _INBOUWDOOS_TYPES)
    if inbouw_count > 0:
        cat = _ANCILLARY_CATALOGUE["inbouwdoos_enkel"]
        lines.append(
            MaterialLine(
                symbol_id="ancillary",
                symbol_type=SymbolType.ONBEKEND,
                etim_code=cat["etim_code"],
                description=cat["description"],
                quantity=inbouw_count,
                unit=cat["unit"],
                unit_price=cat["unit_price"],
                total_price=round(cat["unit_price"] * inbouw_count, 2),
            )
        )

    # Installatieautomaten (1 per uniek circuit met belasting)
    circuits_with_load = {
        s.circuit
        for s in symbols
        if s.circuit and s.type in {
            SymbolType.WANDCONTACTDOOS, SymbolType.WANDCONTACTDOOS_DUBBEL,
            SymbolType.LICHTPUNT, SymbolType.LICHTPUNT_SPOT,
        }
    }
    if circuits_with_load:
        cat = _ANCILLARY_CATALOGUE["zekering_b16"]
        qty = len(circuits_with_load)
        lines.append(
            MaterialLine(
                symbol_id="ancillary",
                symbol_type=SymbolType.ONBEKEND,
                etim_code=cat["etim_code"],
                description=cat["description"],
                quantity=qty,
                unit=cat["unit"],
                unit_price=cat["unit_price"],
                total_price=round(cat["unit_price"] * qty, 2),
            )
        )

    # Aardlekschakelaars (1 per 4 groepen)
    import math
    n_diff = math.ceil(len(circuits_with_load) / 4) if circuits_with_load else 0
    if n_diff > 0:
        cat = _ANCILLARY_CATALOGUE["diff_30ma"]
        lines.append(
            MaterialLine(
                symbol_id="ancillary",
                symbol_type=SymbolType.ONBEKEND,
                etim_code=cat["etim_code"],
                description=cat["description"],
                quantity=n_diff,
                unit=cat["unit"],
                unit_price=cat["unit_price"],
                total_price=round(cat["unit_price"] * n_diff, 2),
            )
        )

    return lines
