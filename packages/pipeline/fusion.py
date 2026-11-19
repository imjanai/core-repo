"""
packages/pipeline/fusion.py — stap 6: drie sporen → één Project.

De vector-parser, de detector en de VLM kijken allemaal naar dezelfde tekening
en leveren allemaal `Symbol`-objecten. Zonder fusie krijgt de elektricien
drie keer dezelfde contactdoos in zijn materiaallijst.

Wat deze module doet:

1. **Ruis eruit.** Symbolen onder `min_confidence` (alleen van detector/VLM —
   vector en menselijke correcties vertrouwen we blind) worden verwijderd.
2. **Samensmelten.** Symbolen van hetzelfde type die binnen
   `merge_distance_mm` van elkaar liggen worden één symbool:
   positie = gewogen gemiddelde, confidence = opgeteld tot 0.99, en het
   best krijgt voorrang volgens `source_priority` (vector > detector > vlm >
   human). De herkomst blijft bewaard in `attributes` voor de review-UI.
3. **Ruimtes toewijzen.** Symbolen zonder `room_id` worden via
   point-in-polygon (ray casting) aan een ruimte gekoppeld — zo kan de
   AREI-regel "rookmelder in elke slaapkamer" überhaupt werken.

De functie is puur: geen I/O, geen model, deterministisch. Daardoor is hij
met property-based tests te dekken.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from packages.schema import Project, SourceType, Symbol, SymbolType

#: Bronnen in opklimmende betrouwbaarheid (later = beter bij gelijke score).
SOURCE_RANK: dict[str, int] = {
    SourceType.VECTOR.value: 0,
    SourceType.DETECTOR.value: 1,
    SourceType.VLM.value: 2,
    SourceType.HUMAN.value: 3,
    "vector": 0,
    "detector": 1,
    "vlm": 2,
    "human": 3,
}


@dataclass
class FusionConfig:
    merge_distance_mm: float = 150.0
    min_confidence: float = 0.35
    assign_rooms: bool = True
    confidence_boost: float = 0.10
    max_confidence: float = 0.99
    #: bronnen die we zonder drempel vertrouwen
    trusted_sources: tuple[str, ...] = ("vector", "human")
    source_priority: tuple[str, ...] = ("human", "vector", "detector", "vlm")
    exclude_types: tuple[SymbolType, ...] = field(default_factory=tuple)


@dataclass
class FusionStats:
    input_count: int = 0
    dropped_low_confidence: int = 0
    merged: int = 0
    output_count: int = 0
    rooms_assigned: int = 0
    dropped_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "input_count": self.input_count,
            "output_count": self.output_count,
            "dropped_low_confidence": self.dropped_low_confidence,
            "merged": self.merged,
            "rooms_assigned": self.rooms_assigned,
            "dropped_ids": self.dropped_ids,
        }


# ---------------------------------------------------------------------------
# Publieke API
# ---------------------------------------------------------------------------


def fuse(project: Project, config: FusionConfig | None = None) -> tuple[Project, FusionStats]:
    """Voert de fusie uit en geeft (project, statistieken) terug."""
    cfg = config or FusionConfig()
    stats = FusionStats(input_count=len(project.symbols))

    kept: list[Symbol] = []
    for sym in project.symbols:
        if sym.type in cfg.exclude_types:
            stats.dropped_ids.append(sym.id)
            stats.dropped_low_confidence += 1
            continue
        source = _source_value(sym)
        if source not in cfg.trusted_sources and sym.confidence < cfg.min_confidence:
            stats.dropped_ids.append(sym.id)
            stats.dropped_low_confidence += 1
            continue
        kept.append(sym)

    merged: list[Symbol] = []
    for sym in kept:
        target = _find_neighbor(sym, merged, cfg)
        if target is None:
            merged.append(sym)
            continue
        _merge_into(target, sym, cfg)
        stats.merged += 1

    if cfg.assign_rooms:
        stats.rooms_assigned = assign_rooms(merged, project.rooms)

    stats.output_count = len(merged)
    project.symbols = merged
    project.meta = dict(project.meta or {})
    project.meta["fusion"] = stats.as_dict()
    return project, stats


def assign_rooms(symbols: list[Symbol], rooms: list) -> int:
    """Koppelt symbolen zonder ruimte aan de ruimte waarin ze liggen."""
    if not rooms:
        return 0
    assigned = 0
    for sym in symbols:
        if sym.room_id:
            continue
        for room in rooms:
            if point_in_polygon(sym.x, sym.y, room.polygon):
                sym.room_id = room.id
                assigned += 1
                break
    return assigned


def point_in_polygon(x: float, y: float, polygon: list) -> bool:
    """
    Ray casting (even-odd rule).

    Werkt ook met concave polygonen en heeft geen externe afhankelijkheid —
    een library als shapely is voor één vraag "ligt dit punt in deze ruimte?"
    een zware investering.
    """
    if not polygon or len(polygon) < 3:
        return False

    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = _xy(polygon[i])
        xj, yj = _xy(polygon[j])
        if (yi > y) != (yj > y):
            x_cross = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def distance(a: Symbol, b: Symbol) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


# ---------------------------------------------------------------------------
# Intern
# ---------------------------------------------------------------------------


def _xy(point) -> tuple[float, float]:
    if isinstance(point, (list, tuple)):
        return float(point[0]), float(point[1])
    return float(point.x), float(point.y)


def _source_value(sym: Symbol) -> str:
    src = sym.source
    return src.value if isinstance(src, SourceType) else str(src)


def _rank(sym: Symbol) -> int:
    return SOURCE_RANK.get(_source_value(sym), 9)


def _find_neighbor(sym: Symbol, existing: list[Symbol], cfg: FusionConfig) -> Symbol | None:
    best: Symbol | None = None
    best_dist = cfg.merge_distance_mm
    for other in existing:
        if other.type != sym.type:
            continue
        d = distance(sym, other)
        if d <= best_dist:
            best, best_dist = other, d
    return best


def _merge_into(target: Symbol, incoming: Symbol, cfg: FusionConfig) -> None:
    """
    Slimt `incoming` op in `target`.

    Positie: gewogen met confidence — een zekere vondst trekt zwaarder dan
    een twijfelgeval. Confidence: onafhankelijke bevestigingen stapelen op
    (tot `max_confidence`), zodat "detector én VLM zagen hetzelfde" telt.
    """
    wt = max(target.confidence, 1e-6)
    wi = max(incoming.confidence, 1e-6)
    target.x = (target.x * wt + incoming.x * wi) / (wt + wi)
    target.y = (target.y * wt + incoming.y * wi) / (wt + wi)

    # Beter bron eerst (lagere rank = beter).
    if _rank(incoming) < _rank(target):
        target.source = incoming.source
        target.confidence = incoming.confidence
        target.attributes = {**incoming.attributes, **target.attributes}
    else:
        target.attributes = {**target.attributes, **incoming.attributes}

    target.confidence = min(
        cfg.max_confidence,
        max(target.confidence, incoming.confidence) + cfg.confidence_boost,
    )

    if target.room_id is None:
        target.room_id = incoming.room_id
    if target.circuit is None:
        target.circuit = incoming.circuit

    merged_from = list(target.attributes.get("merged_from", []))
    merged_from.append(incoming.id)
    target.attributes["merged_from"] = merged_from
    target.attributes["sources"] = sorted(
        set(target.attributes.get("sources", [])) | {_source_value(incoming), _source_value(target)}
    )
