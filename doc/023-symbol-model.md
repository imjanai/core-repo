# 023 — Het `Symbol`-model

## De code

```python
# packages/schema/symbol.py
from pydantic import BaseModel, Field
from enum import Enum

class SymbolType(str, Enum):
    WCD = "wandcontactdoos"
    SWITCH = "schakelaar"
    LIGHT = "lichtpunt"
    DATA = "datapunt"
    PANEL = "verdeler"


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

## Veld per veld

### `id: str`

Stabiele identificator, gegenereerd bij fusie. **Nooit wijzigen**, ook niet als het type later wordt gecorrigeerd: de id is de sleutel waarmee reviews en trainingsdata aan de waarneming gekoppeld blijven. Zie [015-dataflow-eind-tot-eind](015-dataflow-eind-tot-eind.md).

### `type: SymbolType`

De classificatie. Beperkt tot vijf typen — bewust klein gehouden; uitbreiden gebeurt met een Enum-uitbreiding en een bijbehorende detector-klasse. Zie [025-symboltype-enum](025-symboltype-enum.md).

### `x: float`, `y: float`

Positie in millimeters op de tekening. Niet in pixels, niet in DXF-eenheden: in **mm**, gecorrigeerd met `Project.scale`. Dat maakt het model bruikbaar over formaten heen.

**Ontbrekend:** `rotation` en eventueel `layer`. Een schakelaar die andersom staat is visueel anders maar dezelfde classificatie; voor tekenen via MCP is rotatie wel nodig. Zie [056-mcp-tools](056-mcp-tools.md).

### `room_id: str | None`

Koppeling naar `Room.id`. Wordt bij fusie ingevuld door ruimte-in-de-polygoon-testen. `None` = buiten een herkende ruimte (gang, technische ruimte, of fout).

### `circuit: str | None`

De groep waartoe het punt behoort, bv. `"G3"`. Uit de legenda, uit kabelroutes, of afgeleid door het VLM.

**Waarom dit veld er is:** de regelengine heeft het nodig — zie `max_wcd_per_group` in [packages/rules/rules.py](../packages/rules/rules.py), die per groep telt. Zonder `circuit` kan die regel niet draaien.

### `confidence: float`

Hoe zeker de waarneming is, 0–1.

| Bron | Verwacht bereik |
|---|---|
| `vector` | 1.0 (exact uit DXF) |
| `detector` | 0.5–0.98 (modeldrempel) |
| `vlm` | interpretatief |
| `human` | 1.0 (vastgelegd door vakman) |

**Let op:** er is geen validatie op 0–1. Voeg toe:

```python
confidence: float = Field(default=1.0, ge=0.0, le=1.0)
```

Dat voorkomt stille datacorruptie. Zie [028-validatie-in-het-schema](028-validatie-in-het-schema.md).

### `source: str`

Herkomst: `vector | detector | vlm | human`. Nu een gewone string — een Enum zou compiler-vingers geven. Aanbevolen verbetering:

```python
class SymbolSource(str, Enum):
    VECTOR = "vector"
    DETECTOR = "detector"
    VLM = "vlm"
    HUMAN = "human"
```

**Waarom `source` ertoe doet:** het is de audittrail van elke waarneming. Ermee kun je:

- debugging: "waarom staat er hier een WCD?" → `source=vlm`, laag confidence.
- evaluatie: hoeveel van de materiaallijst berust op exacte data?
- vertrouwen: `vector` en `human` wegen zwaarder in de fusie.

## Wat het model nog niet dekt

| Behoefte | Voorbeeld |
|---|---|
| Rotatie | Voor tekenen via MCP |
| Type-zekerheid per alternatief | `alternatives: list[{type, confidence}]` |
| Koppeling aan detectie-box | `bbox` voor de review-UI |
| Hoogte / verdieping | Bij meerdere bouwlagen |
| Aarding / type stopcontact | Voor een exactere materiaallijst (perilex, randaarde) |
| Fabrikant/serie | Alles zou het tekenwerk versimpelen |

Prioriteer op basis van de MVP: `rotation` en `bbox` zijn het snelst nuttig. Zie [029-schema-uitbreiden](029-schema-uitbreiden.md) voor hoe je ze toevoegt zonder bestaande data te breken.
