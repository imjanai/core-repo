"""
packages/schema — единый Pydantic-projectmodel voor het hele platform.
Alle onderdelen (API, worker, MCP-server) lezen en schrijven dit model.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumeraties
# ---------------------------------------------------------------------------


class SymbolType(str, Enum):
    # --- Contactdozen & schakelaars ---
    WANDCONTACTDOOS = "wandcontactdoos"           # standaard 16A 2P+A
    WANDCONTACTDOOS_DUBBEL = "wandcontactdoos_dubbel"   # dubbel opbouw/inbouw
    WANDCONTACTDOOS_WATERDICHT = "wandcontactdoos_waterdicht"  # IP44/IP55
    WANDCONTACTDOOS_KRACHT = "wandcontactdoos_kracht"  # 16/32A 3P+N+A
    SCHAKELAAR = "schakelaar"                     # enkelpolig
    SCHAKELAAR_WISSEL = "schakelaar_wissel"       # wisselschakelaar
    SCHAKELAAR_KRUIS = "schakelaar_kruis"         # kruisschakelaar
    SCHAKELAAR_DIMMER = "schakelaar_dimmer"
    SCHAKELAAR_TIJDSCHAKELAAR = "schakelaar_tijdschakelaar"
    BEWEGINGSMELDER = "bewegingsmelder"           # PIR wand/plafond
    DRUKKNOP = "drukknop"                         # bel / impulsrelais

    # --- Verlichting ---
    LICHTPUNT = "lichtpunt"                       # plafondlamp algemeen
    LICHTPUNT_SPOT = "lichtpunt_spot"             # inbouwspot
    LICHTPUNT_TL = "lichtpunt_tl"                 # TL/LED-balk
    LICHTPUNT_BUITEN = "lichtpunt_buiten"         # buitenverlichting
    NOODVERLICHTING = "noodverlichting"            # autonome noodverlichtingsarmatuur
    NOODVERLICHTING_PICTOGRAM = "noodverlichting_pictogram"  # vluchtweg-pictogram

    # --- Beveiliging & detectie ---
    ROOKMELDER = "rookmelder"
    KOOLMONOXIDEMELDER = "koolmonoxidemelder"
    HITTEMELDER = "hittemelder"
    GASDETECTOR = "gasdetector"
    ALARMPANEEL = "alarmpaneel"
    MAGNEETCONTACT = "magneetcontact"             # deur-/raamcontact
    SIRENE = "sirene"                             # intern/extern

    # --- Verdeling & beveiliging ---
    VERDELER = "verdeler"                         # sub-verdeelkast ≤24 mod
    GROEPENKAST = "groepenkast"                   # hoofdverdeelkast ≥24 mod
    ZEKERING = "zekering"                         # installatieautomaat
    AARDLEKSCHAKELAAR = "aardlekschakelaar"       # DDR 30mA
    AARDLEKAUTOMAAT = "aardlekautomaat"           # RCBO combinatie
    HOOFDSCHAKELAAR = "hoofdschakelaar"
    OVERSPANNINGSBEVEILIGING = "overspanningsbeveiliging"  # SPD type 1/2

    # --- Klimaat & comfort ---
    THERMOSTAAT = "thermostaat"
    VENTILATIEVENTIEL = "ventilatieventiel"       # toe-/afvoerventiel
    VENTILATIEUNIT = "ventilatieunit"             # WTW/MEV-unit
    WARMTEPOMP_AANSLUITING = "warmtepomp_aansluiting"
    LAADPAAL = "laadpaal"                         # EV-laadpunt

    # --- Data & communicatie ---
    DATAPUNT = "datapunt"                         # RJ45 Cat.6
    DATAPUNT_DUBBEL = "datapunt_dubbel"
    TELEFOONPUNT = "telefoonpunt"
    TV_PUNT = "tv_punt"                           # coax/SAT
    AUDIO_PUNT = "audio_punt"                     # multiroom/sonos
    TOEGANGSLEZER = "toegangslezer"               # RFID-lezer

    # --- Speciale installaties ---
    ZONNEPANEEL_OMVORMER = "zonnepaneel_omvormer"
    ACCU_OPSLAG = "accu_opslag"                   # thuisaccu
    AARDINGSPUNT = "aardingspunt"
    POTENTIAALVEREFFENINGSPUNT = "potentiaalvereffeningspunt"
    TRANSFORMATOR = "transformator"
    UPS = "ups"

    # --- Sanitair / domotica ---
    DEURBELDRUKKER = "deurbeldrukker"
    DEURBELINSTALLATIE = "deurbelinstallatie"
    INTERCOM = "intercom"
    VIDEOFOON = "videofoon"

    ONBEKEND = "onbekend"


class SourceType(str, Enum):
    VECTOR = "vector"
    DETECTOR = "detector"
    VLM = "vlm"
    HUMAN = "human"


class ProjectStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class FileType(str, Enum):
    DXF = "dxf"
    IFC = "ifc"
    PDF = "pdf"
    IMAGE = "image"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Bouwstenen
# ---------------------------------------------------------------------------


class Room(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    floor: int = 0
    polygon: list[list[float]] = Field(default_factory=list)  # [[x,y], ...]


class Symbol(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: SymbolType
    x: float  # mm vanuit tekenursprong
    y: float
    room_id: str | None = None
    circuit: str | None = None  # bv. "G3"
    confidence: float = 1.0
    source: SourceType = SourceType.VECTOR
    attributes: dict[str, Any] = Field(default_factory=dict)


class MaterialLine(BaseModel):
    symbol_id: str
    symbol_type: SymbolType
    etim_code: str | None = None
    description: str
    quantity: int
    unit: str = "st"
    unit_price: float | None = None  # EUR
    total_price: float | None = None  # EUR


class ValidationWarning(BaseModel):
    code: str
    severity: str  # "info" | "warning" | "error"
    message: str
    symbol_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Hoofd-projectmodel
# ---------------------------------------------------------------------------


class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    status: ProjectStatus = ProjectStatus.UPLOADED
    file_type: FileType = FileType.UNKNOWN
    scale: float = 1.0  # px-per-mm of vector-eenheid-per-mm
    rooms: list[Room] = Field(default_factory=list)
    symbols: list[Symbol] = Field(default_factory=list)
    materials: list[MaterialLine] = Field(default_factory=list)
    warnings: list[ValidationWarning] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Correctie (feedback van de elektricien → trainingsdata)
# ---------------------------------------------------------------------------


class CorrectionAction(str, Enum):
    ADD = "add"
    REMOVE = "remove"
    CHANGE_TYPE = "change_type"
    MOVE = "move"


class Correction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    action: CorrectionAction
    symbol_id: str | None = None  # bestaand symbool (remove/change/move)
    new_type: SymbolType | None = None
    new_x: float | None = None
    new_y: float | None = None
    comment: str = ""
