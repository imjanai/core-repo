# 028 — Validatie in het schema versus regelcontrole

Twee soorten "controle" lopen door elkaar. Ze verwarren lezers vaak; dit document scheidt ze.

## Pydantic-validatie (structureel)

**Waar:** in de modellen zelf.
**Wat:** klopt de *vorm* van de data?

```python
class Symbol(BaseModel):
    type: SymbolType
    confidence: float = 1.0
```

Als je `Symbol(type="gibberish")` probeert, faalt Pydantic direct. Dat is deterministisch, snel en gratis.

### Wat er nu ontbreekt in `Symbol`

| Veld | Huidig | Aanbevolen |
|---|---|---|
| `confidence` | `float = 1.0` | `Field(default=1.0, ge=0.0, le=1.0)` |
| `x`, `y` | `float` | `Field(..., description="mm op tekening")` — al deels |
| `source` | `str` | Enum `SymbolSource` |
| `circuit` | `str \| None` | Patroon-validatie, bv. `pattern=r"^G\d+$"` |

### Voorbeeld van verbetering

```python
from pydantic import BaseModel, Field

class Symbol(BaseModel):
    id: str
    type: SymbolType
    x: float = Field(..., description="mm op tekening")
    y: float = Field(..., description="mm op tekening")
    room_id: str | None = None
    circuit: str | None = Field(default=None, pattern=r"^G\d+$")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: SymbolSource = SymbolSource.VECTOR
```

Die `pattern` op `circuit` vangt een klassieke bug: "g3" of "Groep 3" in plaats van "G3", waardoor `max_wcd_per_group` twee aparte groepen ziet en de regel nooit afgaat.

## Regelcontrole (domein)

**Waar:** [packages/rules/rules.py](../packages/rules/rules.py).
**Wat:** klopt de *inhoud* volgens NEN 1010?

```python
def max_wcd_per_group(p: Project) -> list[str]:
    counts = Counter(s.circuit for s in p.symbols
                     if s.circuit and s.type == "wandcontactdoos")
    return [f"Groep {g} heeft {n} WCD's (controleer belasting)"
            for g, n in counts.items() if n > 8]
```

Dit faalt niet — het levert *waarschuwingen*. Dat is bewust: een tekening met 9 WCD's op een groep is geen kapotte data, het is een ontwerpkeuze die een vakman moet beoordelen.

## De grens

| | Pydantic | Rules |
|---|---|---|
| Faalt bij | ongeldige vorm | nooit (levert strings) |
| Eigenaar | schema-ontwikkelaar | domeinexpert |
| Verandert met | het datamodel | de norm |
| Getest door | unit-test per model | unit-test per regel + evaluatieset |

**Vuistregel:** als een conditie betekent "deze data kan niet bestaan" → Pydantic. Als het betekent "deze ontwerpkeuze is verdacht" → regel.

## Interactie met de evaluatieset

Regels zijn ook meetbaar: hoeveel waarschuwingen per tekening, hoeveel zijn terecht. Een nieuwe regel moet vóór productie worden getest op de evaluatieset — anders levert hij ruis en negeren gebruikers hem. Zie [047-rules-nen-1010](047-rules-nen-1010.md) en [069-metrics](069-metrics.md).
