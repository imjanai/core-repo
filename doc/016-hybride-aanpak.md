# 016 — De hybride aanpak

## De kern

> Vectortekeningen worden exact uitgelezen; het VLM is er voor raster en voor interpretatie.

Dit document verklaart *waarom* dat de enige juiste verdeling is.

## Twee soorten invoer, twee soorten waarheid

### Vector (DXF, IFC, vector-PDF)

Een DXF zegt letterlijk: "blok `WCD-01` op laag `E-WCD`, op (12450.0, 8300.0)". Dat is **exacte data**. Een model laten raden naar die coördinaten voegt alleen maar ruis toe — het model zou 12450.0 kunnen voorspellen als 12448.7, en dan klopt de maatvoering niet meer.

**Regel:** als vectordata beschikbaar is, is die leidend. Geen uitzondering.

### Raster (gescande PDF, foto met de telefoon)

Een gescande tekening heeft alleen pixels. Dan is er geen exacte bron, en moet er waargenomen worden: detector + OCR + VLM. Hier is het model onvermijdelijk.

## Wat elk spoor kan en niet kan

| Taak | Vector-parser | Detector | VLM |
|---|---|---|---|
| Exacte coördinaten | ✅ | ❌ | ❌ |
| Aantal symbolen tellen | ✅ | ⚠️ (ruis) | ❌ (slecht) |
| Laag- en bloknamen lezen | ✅ | ❌ | ❌ |
| Symbool herkennen op pixels | ❌ | ✅ | ⚠️ |
| Legenda interpreteren | ❌ | ❌ | ✅ |
| Ruimtes afleiden uit context | ❌ | ❌ | ✅ |
| Twijfelgevallen uitleggen | ❌ | ❌ | ✅ |
| Normregels controleren | ❌ | ❌ | ❌ (code) |

De lege cellen zijn het hele argument: geen enkel spoor dekt alles, en wat code moet doen staat bewust buiten alle drie.

## De verkeerde alternatieven

### "Alleen een model"

Probleem:
- telt onbetrouwbaar (LLM's zijn berucht slecht in tellen),
- kan geen garanties geven over coördinaten,
- duur per tekening (GPU-tijd voor werk dat een parser in milliseconden doet),
- niet deterministisch — dezelfde tekening kan twee keer anders uitkomen.

### "Alleen code"

Probleem:
- werkt niet op gescand materiaal (en 80% van de praktijk is dat),
- kan geen legenda lezen ("wat betekent deze cirkel?"),
- kan geen ruimtes afleiden,
- breekt bij elke nieuwe tekengewoonte.

### "Regelmatigheid detecteren met CV zonder VLM"

Beter, maar mist de legenda. Twee tekeningen kunnen dezelfde cirkel gebruiken voor verschillende dingen; alleen de legenda onderscheidt ze.

## Hoe de verdeling concreet uitpakt

```
vector beschikbaar?
   ├─ ja ─► parser levert symbolen (source="vector", confidence=1.0)
   │         detector draait niet of alleen ter controle
   │         VLM beantwoordt alleen legenda- en ruimtevragen
   │
   └─ nee ─► detector levert kandidaten (source="detector", 0<conf<1)
              VLM interpreteert legenda, suggereert types, tekent ruimtes
              (source="vlm")
```

`Symbol.source` legt precies vast welk spoor het symbool leverde ([023-symbol-model](023-symbol-model.md)). Zo blijft achteraf zichtbaar hoeveel van een resultaat op exacte data berustte en hoeveel op interpretatie — essentieel voor zowel vertrouwen als debugging.

## Wat dit betekent voor de evaluatie

Omdat de sporen ongelijk zijn, moet de evaluatieset ook ongelijk gemeten worden:

- vectorpad: **nauwkeurigheid van koppeling** (wordt het juiste blok het juiste type?),
- rasterpad: mAP en tellingfout,
- hele pipeline: fout in de uiteindelijke materiaallijst.

Zie [069-metrics](069-metrics.md).

## Praktische consequentie voor de MVP

Begin op het vectorpad (DXF/vector-PDF). Dat is het betrouwbare spoor, het levert direct bruikbare data voor de materiaallijst, en het is goedkoop te testen zonder GPU. Raster en foto's komen daarna, als de evaluatieset en het model volwassen zijn. Zie [009-status-en-roadmap](009-status-en-roadmap.md).
