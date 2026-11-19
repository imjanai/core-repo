from collections import Counter, defaultdict
from math import floor, hypot

from pydantic import BaseModel

from packages.schema import MaterialLine, Symbol


class SymbolChange(BaseModel):
    kind: str
    before: Symbol | None = None
    after: Symbol | None = None


class MaterialChange(BaseModel):
    description: str
    etim_code: str | None
    unit: str
    before: int
    after: int
    delta: int


def match_symbols(
    before: list[Symbol], after: list[Symbol], *, distance: float = 300,
) -> tuple[dict[str, Symbol], set[str], set[str]]:
    """Match mutual, unique neighbours, prioritizing nearly identical positions."""
    remaining_before = {symbol.id: symbol for symbol in before}
    remaining_after = {symbol.id: symbol for symbol in after}
    matches: dict[str, Symbol] = {}
    ambiguous_before: set[str] = set()
    ambiguous_after: set[str] = set()
    for radius, same_type in [(5.0, False), (distance, True)]:
        if radius <= 0:
            continue
        cells = defaultdict(list)
        for symbol in remaining_after.values():
            cells[floor(symbol.x / radius), floor(symbol.y / radius)].append(symbol)
        candidates = defaultdict(list)
        incoming = defaultdict(list)
        for old in remaining_before.values():
            col, row = floor(old.x / radius), floor(old.y / radius)
            for x in range(col - 1, col + 2):
                for y in range(row - 1, row + 2):
                    for new in cells.get((x, y), ()):
                        if same_type and old.type != new.type:
                            continue
                        if hypot(old.x - new.x, old.y - new.y) <= radius:
                            candidates[old.id].append(new)
                            incoming[new.id].append(old.id)

        for old_id, options in candidates.items():
            if len(options) != 1 or len(incoming[options[0].id]) != 1:
                continue
            new = options[0]
            matches[old_id] = new
            del remaining_before[old_id]
            del remaining_after[new.id]

        # An ambiguous close pair must never be resolved by a looser pass.
        ambiguous_old = candidates.keys() & remaining_before.keys()
        ambiguous_new = incoming.keys() & remaining_after.keys()
        ambiguous_before.update(ambiguous_old)
        ambiguous_after.update(ambiguous_new)
        for key in ambiguous_old:
            del remaining_before[key]
        for key in ambiguous_new:
            del remaining_after[key]
    return matches, ambiguous_before, ambiguous_after


def compare_symbols(before: list[Symbol], after: list[Symbol]) -> list[SymbolChange]:
    matches, ambiguous_before, ambiguous_after = match_symbols(before, after)
    matched_ids = {symbol.id for symbol in matches.values()}
    changes = []
    for old in before:
        new = matches.get(old.id)
        if new is None:
            kind = "uncertain" if old.id in ambiguous_before else "removed"
        elif old.type != new.type:
            kind = "retyped"
        elif hypot(old.x - new.x, old.y - new.y) > 5:
            kind = "moved"
        else:
            continue
        changes.append(SymbolChange(kind=kind, before=old, after=new))
    for new in after:
        if new.id not in matched_ids:
            kind = "uncertain" if new.id in ambiguous_after else "added"
            changes.append(SymbolChange(kind=kind, after=new))
    return changes


def compare_materials(before: list[MaterialLine], after: list[MaterialLine]) -> list[MaterialChange]:
    def quantities(lines):
        counts = Counter()
        for line in lines:
            key = (line.description, line.etim_code, line.unit)
            counts[key] += line.quantity
        return counts

    old, new = quantities(before), quantities(after)
    return [
        MaterialChange(description=key[0], etim_code=key[1], unit=key[2],
                       before=old[key], after=new[key], delta=new[key] - old[key])
        for key in sorted(old.keys() | new.keys(), key=lambda key: (key[0], key[1] or "", key[2]))
        if new[key] != old[key]
    ]
