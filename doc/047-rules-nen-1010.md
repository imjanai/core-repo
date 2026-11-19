# 047 — De regelengine en NEN 1010

## Dit is het enige pakket met echte code

[packages/rules/rules.py](../packages/rules/rules.py):

```python
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
```

## Het ontwerp

Een regel is een `Rule` met:

- `id`: stabiele identificatie ("grp-wcd") — bruikbaar in de UI, in tests en in de evaluatie,
- `description`: menselijke omschrijving,
- `check`: een puur function van `Project` naar waarschuwingen.

**Waarom deze vorm goed is:**

- **Uitbreiden = één regel toevoegen.** Geen if-else-keten.
- **Elke regel testbaar** met een handgeschreven `Project`.
- **Elke regel meetbaar** — je kunt per `id` tellen hoe vaak hij afgaat op de evaluatieset.

## De huidige regel: `max_wcd_per_group`

Maximaal 8 wandcontactdoos­sen per groep. Het telt per `circuit` en levert een bericht zodra de drempel overschreden is.

### Wat er ontbreekt

- De grens 8 staat **hardcoded**. Grenswaarden horen uit de norm te komen en door een domeinexpert beheerd te worden — in een config, niet in code. Zie het ontwerpprincipe in de README: *"Normcontrole is regelgebaseerd. Grenswaarden komen uit de geldende norm en worden door een domeinexpert beheerd, niet door het model bepaald."*
- `s.type == "wandcontactdoos"` gebruikt de enum-waarde als string. Dat werkt dankzij `str, Enum`, maar `SymbolType.WCD` is leesbaarder en compileveiliger.
- Er is geen `severity`: elke waarschuwing weegt even zwaar.

## Waar de regelset naartoe moet

| Regel-groep | Voorbeeld | Benodigd veld |
|---|---|---|
| **Belasting** | Som van vermogen per groep ≤ grenswaarde | `Symbol.type`, `circuit`, vermogenstabel |
| **Badkamer-zones** | Installatie in zone 0/1/2 niet toegestaan | `Room.room_type`, `Symbol.x/y`, zone-polygoon |
| **Beveiliging** | Aardlekschakelaar aanwezig in de groepenkast | `Symbol(PANEL)` |
| **Kabeldimensionering** | Doorsnede ≥ vereist voor belasting en lengte | `circuit`, lengte uit tekening |
| **Aarding** | Aarding in elke badkamer | `Room` + `Symbol` |
| **Aantal punten** | Maximaal aantal WCD's per groep (bestaande regel) | `circuit` |

Zie de roadmap Fase 4 in [009-status-en-roadmap](009-status-en-roadmap.md).

## Structuur van waarschuwingen

Nu strings. Beter:

```python
class Waarschuwing(BaseModel):
    rule_id: str
    severity: str                 # info | warn | error
    message: str
    symbol_ids: list[str] = []
    room_id: str | None = None
```

Dat koppelt de waarschuwing aan de tekening en maakt de review-UI bruikbaar. Zie [028-validatie-in-het-schema](028-validatie-in-het-schema.md) en [027-versiebeheer-van-het-schema](027-versiebeheer-van-het-schema.md).

## Bekend bug-achtig detail

De import `from schema import Project` werkt niet in de huidige structuur; het pakket `schema` bestaat niet als zodanig. Zie [026-schema-export](026-schema-export.md) en [030-schema-verschillen-met-readme](030-schema-verschillen-met-readme.md). Dit is de eerste fix die gedaan moet worden.

## Regels testen

```python
def test_max_wcd_regel_vuurt():
    p = Project(id="t", scale=1.0, symbols=[
        Symbol(id=str(i), type=SymbolType.WCD, x=0, y=0, circuit="G1")
        for i in range(9)
    ])
    assert any("G1" in w for w in validate(p))

def test_max_wcd_regel_blijft_stil():
    p = Project(id="t", scale=1.0, symbols=[
        Symbol(id=str(i), type=SymbolType.WCD, x=0, y=0, circuit="G1")
        for i in range(8)
    ])
    assert validate(p) == []
```

Elke nieuwe regel krijgt beide tests: een positief en een negatief geval. Zie [081-teststrategie](081-teststrategie.md).
