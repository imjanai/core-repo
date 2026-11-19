"""
packages/rules/limits.py — configureerbare drempelwaarden per AREI-onderwerp.

Domeinexpert past hier de waarden aan wanneer de AREI-editie wijzigt.
De regellogica hoeft daarvoor niet gewijzigd te worden.

Gebruik:
    from packages.rules.limits import DEFAULT_CONFIG, RulesConfig
    from dataclasses import replace

    # Residentieel (standaard):
    validate(project)

    # Industrieel:
    cfg = replace(DEFAULT_CONFIG, circuit=replace(DEFAULT_CONFIG.circuit, max_wcd=16))
    validate(project, config=cfg, scope="industrial")
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# AREI Art. 4 — groepsleidingen en belasting
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CircuitLimits:
    # AREI Art. 4.4.2 §2 — max contactdozen per groepsleiding
    max_wcd: int = 8
    # Gangbare praktijk — max lichtpunten per groepsleiding
    max_lichtpunten: int = 12
    # AREI Art. 4.4.3 — max krachtstopcontacten per groepsleiding
    max_kracht: int = 4
    # Minimaal aantal WCD's per slaapkamer/woonkamer
    min_wcd_per_room: int = 2
    # Minimaal aantal WCD's per keuken (AREI advies)
    min_wcd_keuken: int = 4
    # Max stroom (A) per verlichtingsgroep
    max_stroom_verlichting_a: float = 16.0


# ---------------------------------------------------------------------------
# AREI Art. 5 — laagspanningsinstallaties, kabeldimensionering
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CableLimits:
    # Minimale doorsnede voedingskabel naar groepenkast (mm²)
    min_hoofdkabel_mm2: float = 10.0
    # Minimale doorsnede groepsleiding verlichting (mm²)
    min_kabel_verlichting_mm2: float = 1.5
    # Minimale doorsnede groepsleiding kracht (mm²)
    min_kabel_kracht_mm2: float = 2.5
    # Minimale doorsnede EV-laadleiding (mm²)
    min_kabel_ev_mm2: float = 6.0
    # Max spanningsval (%) over volledige installatie
    max_spanningsval_pct: float = 4.0


# ---------------------------------------------------------------------------
# AREI Art. 6 — beveiliging tegen elektrische schokken
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SafetyLimits:
    # AREI Art. 6.4.1 — aardlekschakelaar verplicht in woningen
    rcd_required: bool = True
    # Max aanspreekstroom (mA)
    rcd_max_ma: int = 30
    # Gangbare groepering: max N groepen per aardlekschakelaar
    rcd_circuits_per_unit: int = 4
    # AREI Art. 6 — overspanningsbeveiliging verplicht boven drempel (kVA)
    spd_required_above_kva: float = 7.4
    # Potentiaalvereffening verplicht in nat lokaal
    equipotential_in_wet_room: bool = True
    # Minimale IP-klasse contactdozen in badkamer (zone 2)
    min_ip_badkamer_zone2: int = 44


# ---------------------------------------------------------------------------
# AREI Art. 7 — specifieke installaties (noodverlichting, EV, PV)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SpecialInstallationLimits:
    # Noodverlichting autonomie (uur)
    nood_autonomie_h: int = 1
    # Noodverlichting max dekkingsafstand (m) zonder armatuur
    nood_max_afstand_m: float = 15.0
    # EV-laadpaal: vereist eigen aardlekautomaat type B
    ev_requires_type_b_rcd: bool = True
    # PV-installatie: vereist terugleverbeveiliging
    pv_requires_anti_islanding: bool = True
    # UPS vereist bij serverruimte / kritische installatie
    ups_required_server_room: bool = True


# ---------------------------------------------------------------------------
# Brandbeveiliging (NBN S21-208 / AREI Art. 7)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FireSafetyLimits:
    # NBN S21-208 — rookmelder per slaapkamer
    detector_per_bedroom: bool = True
    # Koolmonoxidemelder verplicht bij stookruimte/garage
    co_detector_in_boilerroom: bool = True
    # Noodverlichting verplicht in vluchtroutes
    emergency_light_escape_routes: bool = True
    # Kamernamen die als slaapkamer worden herkend (lowercase, substring)
    bedroom_keywords: tuple[str, ...] = (
        "slaap", "bedroom", "chambre", "dormit", "dorm",
    )
    # Gangen / vluchtroutes
    escape_route_keywords: tuple[str, ...] = (
        "gang", "corridor", "hal", "trap", "hall", "exit",
        "couloir", "escalier", "vlucht",
    )
    # Stookruimtes / garages (CO-melder)
    boiler_room_keywords: tuple[str, ...] = (
        "stook", "ketel", "garage", "chaufferie", "chaudière",
        "boiler", "technisch",
    )


# ---------------------------------------------------------------------------
# Geometrie (tekening-kwaliteitscontroles)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GeometryLimits:
    # Afstand (mm) waarbinnen twee gelijke symbolen als dubbel beschouwd worden
    duplicate_distance_mm: float = 50.0
    # Min. afstand (mm) contactdoos t.o.v. waterleiding (AREI)
    min_afstand_water_mm: float = 150.0


# ---------------------------------------------------------------------------
# Projectniveau
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProjectLimits:
    # Min. symbolen waarboven een verdeler verplicht is
    min_symbols_for_panel: int = 10
    # Min. circuits waarboven een groepenkast verplicht is
    min_circuits_for_kast: int = 4
    # Min. WCD's voor woonkamer (AREI advies leefruimte)
    min_wcd_woonkamer: int = 4
    # Min. WCD's voor keuken
    min_wcd_keuken: int = 6


# ---------------------------------------------------------------------------
# Gecombineerde config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RulesConfig:
    circuit: CircuitLimits = field(default_factory=CircuitLimits)
    cable: CableLimits = field(default_factory=CableLimits)
    safety: SafetyLimits = field(default_factory=SafetyLimits)
    special: SpecialInstallationLimits = field(default_factory=SpecialInstallationLimits)
    fire: FireSafetyLimits = field(default_factory=FireSafetyLimits)
    geometry: GeometryLimits = field(default_factory=GeometryLimits)
    project: ProjectLimits = field(default_factory=ProjectLimits)


# ---------------------------------------------------------------------------
# Standaard-instanties
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = RulesConfig()

INDUSTRIAL_CONFIG = RulesConfig(
    circuit=CircuitLimits(max_wcd=16, max_kracht=8, min_wcd_per_room=0),
    safety=SafetyLimits(rcd_circuits_per_unit=8, rcd_max_ma=300),
    project=ProjectLimits(min_symbols_for_panel=1, min_circuits_for_kast=1),
)

COMMERCIAL_CONFIG = RulesConfig(
    circuit=CircuitLimits(max_wcd=12, max_kracht=6),
    safety=SafetyLimits(rcd_circuits_per_unit=6),
    special=SpecialInstallationLimits(nood_autonomie_h=3),  # AREI kantoor = 3h
)
