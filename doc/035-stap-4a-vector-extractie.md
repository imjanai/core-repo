# 035 — Stap 4a: Vector-extractie

## Wanneer

Alleen bij DXF, IFC en vector-PDF. Bij raster slaat deze stap over.

## Wat er uitkomt

Lijsten waarnemingen met **exacte** coördinaten en metadata — geen gokwerk.

```python
class VectorSymbol(BaseModel):
    layer: str
    block_name: str | None
    x: float
    y: float
    rotation: float = 0.0
    tekst: str | None = None     # bv. "WCD" of een nummer
```

## DXF met ezdxf

Een DXF bevat:

- **INSERT**-entiteiten: verwijzingen naar blokken (de symbolen),
- **TEXT / MTEXT**: labels, ruimtenamen, legenda-tekst,
- **LINE / LWPOLYLINE / ARC**: wanden, kabelroutes,
- **LAYERS**: categorieën zoals `E-WCD`, `E-LICHT`, `A-WANDEN`.

### Wat je eruit haalt

| Waarneemt | Voor |
|---|---|
| INSERT per blok + positie + rotatie | symbool met exacte locatie |
| Bloknaam | klasse-gok ("WCD_01" → wandcontactdoos) |
| Laagnaam | sterk signaal ("E-WCD" → wandcontactdoos) |
| TEXT in de buurt | label of waarden ("G3" → circuit) |
| LWPOLYLINE op wandlagen | kamercontouren → `Room.polygon` |

**Waarom laag- en bloknamen zo waardevol zijn:** veel tekeningen zijn geëxporteerd uit een BIM-tool of een sjabloon, waarin de naamgeving al semantisch is. Dat is gratis labeling. Eén waarschuwing: naamgeving is niet gestandaardiseerd — "WCD", "WS", "STOPCONTACT" komen alle drie voor. Los op met een mapping-tabel plus het VLM voor onbekende namen.

## IFC met ifcopenshell

IFC is rijker: een `IfcElectricOutlet` heeft al een klasse, een relatie naar een ruimte (`IfcSpace`) en een placement in 3D. De extractie is dus grotendeels direct mapping naar `Symbol` — inclusief `room_id`, wat anders door de VLM geraden moet worden.

## Vector-PDF

Het lastigste vectorpad: PDF bevat geen semantiek, alleen grafische operatoren.

1. PyMuPDF levert de vectordata per pagina.
2. Patronen herkennen: een cirkel van radius r op plek p is een kandidaat-symbool.
3. Tekstblokken (pdfplumber) leveren de legenda en labels.

**Resultaat:** een lijst kandidaat-vormen zonder klasse; de koppeling naar type gebeurt in stap 5 (legenda) en 6 (fusie).

## Wat je bewust niet doet

- **Niet rekenen.** De parser telt niet "er zijn 12 WCD's". Hij levert 12 waarnemingen; het tellen gebeurt in de materiaalengine over het gefuseerde `Project`. Zie principe 3 in [006-ontwerpprincipes](006-ontwerpprincipes.md).
- **Niet normaliseren naar mm.** De parser werkt in tekeningseenheden; de schaal-correctie is de verantwoordelijkheid van de fusiestap met `Project.scale`.

## Kwaliteit

Test met een vaste set DXF's en vergelijk de telling tegen handmatig getelde waarden. Meet:

- recall: hoeveel van de werkelijke symbolen worden gevonden?
- precisie: hoeveel gevonden entiteiten zijn echt symbolen?

Dit is de baseline voor het vectorpad in de evaluatieset ([068-evaluatieset](068-evaluatieset.md)).

## Wat er nu bestaat

Niets. [packages/parsers](../packages/parsers) is leeg. Zie [042-parsers-dxf](042-parsers-dxf.md), [043-parsers-ifc](043-parsers-ifc.md), [044-parsers-pdf](044-parsers-pdf.md).
