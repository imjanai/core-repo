from dataclasses import dataclass
from typing import Callable
from schema import Project

# Data class van een regel.
@dataclass
class Rule:
    id: str
    description: str
    check: Callable[[Project], list[str]]

# Hoeveel maximum stopcontacten per groep?
def max_wcd_per_group(p: Project) -> list[str]:
    from collections import Counter
    counts = Counter(s.circuit for s in p.symbols if s.circuit and s.type == "wandcontactdoos")
    return [f"Groep {g} heeft {n} WCD's (controleer belasting)" for g, n in counts.items() if n > 8]

# Voeg dit toe als regel.
RULES = [Rule("grp-wcd", "Max WCD per groep", max_wcd_per_group)]

def validate(p: Project) -> list[str]:
    return [msg for r in RULES for msg in r.check(p)]