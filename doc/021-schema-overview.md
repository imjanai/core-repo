# 021 — Het projectmodel als bron van waarheid

## Wat het is

`packages/schema` bevat de Pydantic-modellen die **alle** onderdelen gebruiken om data uit te wisselen. Geen enkele andere laag definieert zijn eigen versie van "een symbool".

## Waarom dit zo belangrijk is

Principe 2 uit [006-ontwerpprincipes](006-ontwerpprincipes.md): *één bron van waarheid*. Concreet voorkomt het:

- drie verschillende definities van `confidence` (is 80 of 0.8 de norm?),
- frontend en backend die het oneens zijn over wat `circuit` bevat,
- een migratie die één component breekt en de rest niet.

## De modellen

| Model | Bestand | Rol |
|---|---|---|
| `Project` | [project.py](../packages/schema/project.py) | Het geheel |
| `Symbol` | [symbol.py](../packages/schema/symbol.py) | Eén herkend installatiepunt |
| `Room` | [room.py](../packages/schema/room.py) | Eén ruimte met polygoon |
| `SymbolType` | [symbol.py](../packages/schema/symbol.py) | Enum van toegestane typen |

## De code

```python
# packages/schema/project.py
class Project(BaseModel):
    id: str
    scale: float = Field(..., description="mm per tekeningeenheid")
    rooms: list[Room] = []
    symbols: list[Symbol] = []
    warnings: list[str] = []
```

```python
# packages/schema/symbol.py
class Symbol(BaseModel):
    id: str
    type: SymbolType
    x: float                    # in mm, op tekening
    y: float
    room_id: str | None = None
    circuit: str | None = None  # bv. "G3"
    confidence: float = 1.0
    source: str = "vector"      # vector | detector | vlm | human
```

```python
# packages/schema/room.py
class Room(BaseModel):
    id: str
    name: str
    polygon: list[tuple[float, float]]
```

## Wat elk veld betekent voor de rest van het systeem

| Veld | Wie vult het | Wie leest het |
|---|---|---|
| `Project.scale` | normalisatie (stap 3) | alles wat coördinaten omrekent, incl. frontend |
| `Symbol.x/y` | analyse (stap 4/5) | materiaal, tekenengine, review-UI |
| `Symbol.type` | analyse | regels, materiaal, MCP |
| `Symbol.room_id` | fusie (stap 6) | materiaal per ruimte, offerte |
| `Symbol.circuit` | fusie/redenering | regelengine (bijv. `max_wcd_per_group`) |
| `Symbol.confidence` | elke bron apart | reviewprioriteit, drempels |
| `Symbol.source` | elke bron apart | debugging, evaluatie, vertrouwen |
| `Project.warnings` | validatie + fusie | UI, offerte, rapport |

## Ontwerpprincipes in het schema

1. **`confidence` en `source` zijn verplicht door te denken** — elke waarneming moet zeggen hoe zeker hij is en waar hij vandaan komt. Dat maakt fusie en debugging mogelijk.
2. **`scale` staat op `Project`, niet op `Symbol`** — schaal geldt per tekening, niet per symbool. Voorkomt inconsistenties.
3. **`warnings` zijn strings** — nu eenvoudig. Later waarschijnlijk gestructureerd (code + severity + symbol_ids); zie [027](027-versiebeheer-van-het-schema.md).

## Openstaande verbeteringen

- `source` en `circuit` zijn gewone strings; een Enum zou fouten voorkomen. Zie [023-symbol-model](023-symbol-model.md).
- Er is nog geen `__init__.py` die de modellen exporteert. Zie [026-schema-export](026-schema-export.md).
- [packages/rules/rules.py](../packages/rules/rules.py) importeert `from schema import Project` — die import klopt niet met de huidige mappenstructuur. Zie [030-schema-verschillen-met-readme](030-schema-verschillen-met-readme.md).
