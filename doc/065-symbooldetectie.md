# 065 — Symbooldetectie: YOLO versus RT-DETR

## De vergelijking

| | YOLO (Ultralytics) | RT-DETR |
|---|---|---|
| Type | Convolutioneel, één-pass | Transformer-gebaseerd |
| Snelheid | Zeer snel | Trager |
| Detectie bij overlap | Kan missen | Sterker |
| Kleine objecten | Goed met tiling | Goed |
| Train-data behoefte | Matig | Vaak iets meer |
| Onderbreiding | Zeer breed | Nieuwer |
| Export | ONNX, TensorRT, CoreML | ONNX |
| In deze repo | `ultralytics` in dependencies | `transformers` beschikbaar |

Beide staan in de README als optie: "Ultralytics YOLO / RT-DETR".

## Advies

**Begin met YOLO.** Redenen:

1. De kortste weg naar een eerste mAP-cijfer — en meten is het doel ([006-principe 6](006-ontwerpprincipes.md)).
2. De documentatie en het ecosysteem zijn rijker.
3. Export naar TensorRT is goed voor latency.

**Stap over op RT-DETR als** de evaluatieset laat zien dat:

- tekeningen met dicht op elkaar staande symbolen structureel recall verliezen, of
- de NMS-instellingen een bottleneck blijken (RT-DETR heeft geen NMS nodig — het is end-to-end).

Dat is een meetbare overweging, geen smaak. Zie [069-metrics](069-metrics.md).

## De symbolen zijn klein

Een WCD op een A0-tekening is een paar millimeter. Twee mechanismen helpen:

1. **Tiling met SAHI** — zie [036-stap-4b-detectie](036-stap-4b-detectie.md) en [045-vision-detector](045-vision-detector.md).
2. **Hoge resolutie trainen** (`imgsz=1024` of meer) — kost geheugen, maar is het verschil tussen "herkent" en "herkent niet".

## De dataset bepaalt het model

Bij een domein met vijf klassen en veel herhaling is een klein model vaak genoeg. Het geld gaat naar **datakwaliteit**, niet naar modelgrootte:

- betere labels,
- meer variatie (verschillende tekengewoonten, exporten, schalen),
- de moeilijke gevallen expliciet opnemen.

Zie [067-labeling](067-labeling.md).

## Wat je per klasse meet

mAP gemiddeld over klassen verbergt veel. Rapporteer per klasse:

| Klasse | Verwachte moeilijkheid |
|---|---|
| `verdeler` | Makkelijk — groot, uniek |
| `lichtpunt` | Middel — klein, veel |
| `wandcontactdoos` | Middel — klein, veel, opvallend |
| `schakelaar` | Moeilijk — lijkt op WCD |
| `datapunt` | Moeilijk — lijkt op WCD |

De verwarring WCD/schakelaar/datapunt is precies waar de legenda en het VLM de detector komen helpen: een legenda-crop bij de classificatie voegen verhoogt de nauwkeurigheid aanzienlijk. Zie [037-stap-4c-tekst-en-legenda](037-stap-4c-tekst-en-legenda.md).

## Wat er nu bestaat

Niets. [ml/train_detector.py](../ml/train_detector.py) is leeg.
