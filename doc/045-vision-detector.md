# 045 — Symbooldetectie: YOLO / RT-DETR met SAHI

## De rol

De detector is het snelste spoor voor rasterinvoer: hij doorzoekt een afbeelding en levert bounding boxes met klassen. Waar het VLM seconden per crop kost, doet YOLO duizenden objecten per seconde.

## De keuze: YOLO versus RT-DETR

| | YOLO (Ultralytics) | RT-DETR |
|---|---|---|
| Architectuur | Convolutioneel, één-pass | Transformer-gebaseerd |
| Snelheid | Zeer snel | Trager |
| Bij drukke tekeningen | Kan overlappende symbolen missen | Sterker bij overlap |
| Onderbreiding | Zeer breed, veel voorbeelden | Nieuwer, kleiner ecosysteem |
| Export | ONNX, TensorRT, gemakkelijk | ONNX mogelijk |

**Advies:** begin met YOLO voor de baseline (snel, veel documentatie, eenvoudig te exporteren). Houd RT-DETR als optie als de evaluatieset laat zien dat overlap een knelpunt is. Zie [065-symbooldetectie](065-symbooldetectie.md) voor de vergelijking.

## SAHI: tiling voor grote tekeningen

Zonder tegelen wordt een A0-tekening geschaald tot onherkenbaarheid. SAHI (Slicing Aided Hyperparameter Inference) snijdt in overlappende tegels:

```python
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction

detection_model = AutoDetectionModel.from_pretrained(
    model_type="ultralytics",
    model_path="best.pt",
)

result = get_sliced_prediction(
    image="pagina.png",
    detection_model=detection_model,
    slice_height=1024,
    slice_width=1024,
    overlap_height_ratio=0.2,
    overlap_width_ratio=0.2,
)
```

De coördinaten worden automatisch teruggeprojecteerd naar het originele beeld; SAHI doet ook de non-maximum suppression over tegels heen.

## Drempel en NMS

Twee knoppen die het gedrag sterk beïnvloeden:

- **Confidence-drempel:** te laag = valse positieven in de materiaallijst; te hoog = gemiste punten. Begin hoog (precisie) en toon "mogelijk gemist" apart in de review.
- **NMS-IoU:** bij tekeningen is overlap tussen symbolen legitiem (WCD naast schakelaar). Test zorgvuldig; een te agressieve NMS gooit echte waarnemingen weg.

Zie [036-stap-4b-detectie](036-stap-4b-detectie.md) en [069-metrics](069-metrics.md).

## Inference in de pipeline

```python
class Detector:
    def __init__(self, model_path: str, device: str = "cuda"):
        ...

    def detect(self, image_path: str) -> list[Detection]:
        ...
```

Regels:

- **Laad het model één keer** bij worker-start, niet per taak.
- **Batch-verwerking** over tegels; dat benut de GPU.
- **Determinisme:** zet `torch.manual_seed` en model in eval-mode, zodat dezelfde invoer hetzelfde oplevert.

## Exporteren voor productie

Training in PyTorch, serving kan in meerdere vormen:

| Vorm | Voordeel |
|---|---|
| PyTorch `.pt` | Eenvoudigste; draait in de worker |
| ONNX | Lichter, portabel |
| TensorRT | Snelste op NVIDIA GPU |

Begin met `.pt` in de worker; optimaliseer pas als latency een probleem wordt. Zie [097-prestaties-en-schaal](097-prestaties-en-schaal.md).

## Wat er nu bestaat

Niets. [packages/vision](../packages/vision) is leeg; [ml/train_detector.py](../ml/train_detector.py) is een leeg bestand; `ultralytics` en `sahi` staan in [pyproject.toml](../pyproject.toml).
