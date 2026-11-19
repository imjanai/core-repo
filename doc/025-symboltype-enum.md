# 025 — De `SymbolType`-enum

## De code

```python
class SymbolType(str, Enum):
    WCD = "wandcontactdoos"
    SWITCH = "schakelaar"
    LIGHT = "lichtpunt"
    DATA = "datapunt"
    PANEL = "verdeler"
```

## Waarom een Enum en geen vrije string

- **Compiler-hulp:** een typo wordt gevonden bij het typen, niet bij de klant.
- **Consistentie over sporen heen:** de detector voorspelt klassen, de legenda levert namen, het VLM suggereert types — alle drie moeten op dezelfde waarde uitkomen.
- **Volledigheid:** nieuwe typen worden expliciet toegevoegd, geen stille varianten ("wandcontactdoos", "WCD", "wandcontactdoos (aard)").

Merk op dat `str, Enum` gekozen is: de waarden zijn strings, dus `SymbolType.WCD == "wandcontactdoos"` is `True`. Dat maakt serialisatie en vergelijkingen eenvoudig.

## De vijf typen, in de praktijk

| Enum | Waarde | Wat het is | Aantal typisch per woning |
|---|---|---|---|
| `WCD` | `wandcontactdoos` | Stopcontact | 20–60 |
| `SWITCH` | `schakelaar` | Lichtschakelaar | 8–25 |
| `LIGHT` | `lichtpunt` | Verlichtingspunt (plafond) | 8–30 |
| `DATA` | `datapunt` | Netwerk/TV/telefoon | 2–15 |
| `PANEL` | `verdeler` | Groepenkast / zekeringkast | 1–3 |

## Waar de set bewust klein is

De eerste versie dekt de dominante gevallen. Elke nieuwe klasse betekent:

- labelwerk in de dataset ([067-labeling](067-labeling.md)),
- een nieuwe detector-klasse (hertraining),
- een nieuwe materiaal­koppeling ([048-materials-engine](048-materials-engine.md)),
- eventueel nieuwe regels ([047-rules-nen-1010](047-rules-nen-1010.md)).

Dus: uitbreiden gebeurt op basis van pilotdata, niet op onderbuikgevoel.

## Waarschijnlijke uitbreidingen

| Type | Waarom |
|---|---|
| `MOTION` (`bewegingsschakelaar`) | Veelvoorkomend, eigen materiaal |
| `DIMMER` | Eigen artikel, ander gedrag |
| `VENT` (`ventilatiepunt`) | Bij mechanische ventilatie |
| `SMOKE` (`rookmelder`) | Verplicht in nieuwbouw (NL) |
| `HEATER` (`vloerverwarming-actuator`) | Bij CV-installaties |
| `DOOR_BELL` (`deurbel`) | Klein maar gebruikelijk |
| `EXTRA` (`extra inbouwdoos`) | Lege doos; telt mee voor materiaal maar niet voor belasting |
| `UNKNOWN` | Vangnet voor onbekende detecties — zie hieronder |

### Over `UNKNOWN`

Overweeg expliciet een `UNKNOWN`-type. Zonder vangnet dwingt elke detectie tot een keuze uit de vijf, wat leidt tot foutpositieven in de materiaallijst. Met `UNKNOWN`:

- verdwijnt twijfel uit de betrouwbare categorieën,
- kan de review-UI "onbekend" als eerste prioriteit tonen,
- blijft de trainingsdata schoon.

## Hoe voeg je een type toe (stappenplan)

1. Voeg de waarde toe aan `SymbolType`.
2. Voeg de klasse toe aan de detector-labelset en markeer bestaande labels als "ongebruikt" (niet verwijderd).
3. Voeg een materiaalkoppeling toe in `packages/materials`.
4. Voeg een regel toe als het type belasting raakt.
5. Voeg een symboolweergave toe in `packages/drawing` en de frontend.
6. **Hertrain de detector** met de nieuwe klasse; test op de evaluatieset.
7. Voeg testgevallen toe in `packages/rules` en `packages/materials`.

Zie ook [029-schema-uitbreiden](029-schema-uitbreiden.md).
