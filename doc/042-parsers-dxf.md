# 042 — DXF-parsing met ezdxf

## Waarom DXF de beste invoer is

DXF is tekstgebaseerd en open. Een DXF uit een BIM-tool of een modern CAD-programma bevat de symbolen als blokverwijzingen met exacte coördinaten, laagnamen en soms attributen. Dat is de droom-invoer: geen interpretatie nodig.

## De bibliotheek: ezdxf

```python
import ezdxf

doc = ezdxf.readfile("tekening.dxf")
msp = doc.modelspace()
```

ezdxf kan lezen, schrijven en renderen. Voor parsing is het lezen voldoende; voor [049-drawing-engine](049-drawing-engine.md) komt het schrijven terug.

## Wat je uit een DXF haalt

### INSERT — de symbolen

```python
for insert in msp.query("INSERT"):
    symbool = VectorSymbol(
        layer=insert.dxf.layer,
        block_name=insert.dxf.name,
        x=insert.dxf.insert.x,
        y=insert.dxf.insert.y,
        rotation=insert.dxf.rotation,
    )
```

### TEXT en MTEXT — labels

```python
for text in msp.query("TEXT MTEXT"):
    ...
```

Levert ruimtenamen, groepsnummers, schaalaanduiding, legenda-sleutels.

### LWPOLYLINE — wanden en kabelroutes

Kamercontouren voeden `Room.polygon`; kabelroutes vullen `Symbol.circuit`.

### LAYERS — semantiek

```python
for layer in doc.layers:
    print(layer.dxf.name)
```

Laagnamen als `E-WCD`, `E-LICHT`, `A-WANDEN` zijn een sterk signaal voor de classificatie.

## De valkuilen

| Valkuil | Uitleg | Oplossing |
|---|---|---|
| **Verschillende DXF-versies** | R12 t/m 2018, allemaal anders gedrag | Test met bestanden uit meerdere bronnen |
| **Verschillende eenheden** | `$INSUNITS` (1=inches, 4=mm, 6=m) | Lees `$INSUNITS` en normaliseer; zie [034](034-stap-3-normalisatie.md) |
| **Explode-blokken** | Sommige exporten knippen symbolen in losse lijnen | Herken patronen of val terug op de detector |
| **Bloated bestanden** | AutoCAD plakt complete bibliotheken | Filter op zichtbare lagen |
| **Gesloten lagen** | Symbolen op een uitgeschakelde laag | Controleer `layer.is_off()` en `layer.is_frozen()` |
| **XREF's** | Verwijzingen naar andere bestanden | Optie: inlezen; of: waarschuwing |
| **Geen bloknamen (geëxplodeerd)** | Alleen lijnen en cirkels | Valt terug op vormherkenning + VLM |

## De output

```python
class VectorSymbol(BaseModel):
    layer: str
    block_name: str | None
    x: float
    y: float
    rotation: float = 0.0
    tekst: str | None = None
```

Zie [035-stap-4a-vector-extractie](035-stap-4a-vector-extractie.md).

## Testen

Schrijf een test-DFX met ezdxf (dat kan: ezdxf schrijft ook), plaats daarin drie INSERT's op bekende posities, en verifieer dat de parser ze terugvindt met de juiste coördinaten. Dat geeft een deterministische test zonder dataset.

Daarnaast: een handvol echte tekeningen uit pilotklanten als integratietest, met handmatig getelde aantallen als verwachting.

## Wat er nu bestaat

Niets. [packages/parsers](../packages/parsers) is leeg; `ezdxf` staat wel in [pyproject.toml](../pyproject.toml).
