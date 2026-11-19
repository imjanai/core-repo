# 024 — Het `Room`-model

## De code

```python
# packages/schema/room.py
from pydantic import BaseModel, Field
from enum import Enum

class Room(BaseModel):
    id: str
    name: str
    polygon: list[tuple[float, float]]
```

## Veld per veld

### `id: str`

Stabiele identificator, net als bij `Symbol`.

### `name: str`

Mensenleesbare naam: "Woonkamer", "Badkamer", "Technische ruimte". Komt uit:

- **vector**: tekstblokken in de DXF (ruimtenamen zijn vaak tekst op de tekening),
- **VLM**: interpretatie van context ("deze ruimte met douche en wastafel is de badkamer"),
- **legenda**: soms expliciet genummerd.

### `polygon: list[tuple[float, float]]`

De omtrek als lijst van (x, y)-punten in mm. Dit is een *ring*: het eerste punt sluit impliciet op het laatste.

**Voorbeeld van een rechthoekige kamer:**

```python
Room(id="r1", name="Woonkamer", polygon=[
    (0.0, 0.0), (5200.0, 0.0), (5200.0, 4100.0), (0.0, 4100.0)
])
```

**Waarom een lijst en niet `shapely` of GeoJSON:** geen extra dependency in het schema, en simpel te serialiseren. De keerzijde: geometrische operaties (punt-in-polygoon, overlap) moeten door de gebruiker zelf of via een library worden gedaan. Zie [029-schema-uitbreiden](029-schema-uitbreiden.md) voor de afweging.

## Waarom ruimtes ertoe doen

### 1. Materiaallijst per ruimte

"3 WCD's in de woonkamer, 1 in de badkamer" is nuttiger dan een totaal. Offertes worden per ruimte begroot.

### 2. Normcontrole per ruimte

Badkamers hebben zones (NEN 1010 zone-indeling) die de toegestane installatie bepalen. Zonder `Room` kan die regel niet draaien. Zie [047-rules-nen-1010](047-rules-nen-1010.md).

### 3. Ruimte-in-polygoon bij fusie

Symbolen worden aan de ruimte gekoppeld die hun coördinaat bevat. Dat gebeurt bij fusie (stap 6), niet door het model zelf. Zie [039-stap-6-fusie](039-stap-6-fusie.md).

### 4. Review

De vakman ziet "Badkamer: 4 punten" en kan per ruimte lopen. Efficiënter dan één lange lijst.

## Wat er nog ontbreekt

| Veld | Waarom |
|---|---|
| `floor` / `level` | Gebouwen met meerdere bouwlagen |
| `area_m2` | Berekenbaar uit de polygoon; handig voor belasting en prijs |
| `room_type` | Enum: wonen, bad, keuken, technisch, outdoor — voedt de zone-regels |
| `parent_id` | Onderverdeling (badkamer in woning) |

## Open ontwerpvragen

1. **Moet `Room` een shapely-geometrie gebruiken?** Het zou punt-in-polygoon eenvoudig maken, maar voegt een zware dependency toe aan het schema dat ook door de frontend wordt gelezen. Optie: houd `polygon` in het schema, gebruik shapely alleen in `packages/rules` en de fusiestap.

2. **Wat als een symbool op een scheidingslijn valt?** Kies dan de dichtstbijzijnde ruimtemiddelpunt, en log een waarschuwing — niet stille willekeur.

3. **Hoe om te gaan met gangen?** Gangen hebben vaak geen naam op de tekening. Sta `name=""` toe of voeg een default toe.
