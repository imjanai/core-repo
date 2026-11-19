# 061 — De ML-kant in het kort

## Wat er getraind wordt

| Model | Taak | Script |
|---|---|---|
| **Symbooldetector** | Bounding boxes + klassen op afbeeldingen | [ml/train_detector.py](../ml/train_detector.py) (leeg) |
| **VLM (Qwen-VL)** | Legenda, context, ruimtes, twijfelgevallen | [ml/finetune_vlm.py](../ml/finetune_vlm.py) (leeg) |

Twee modellen, twee disciplines: detectie is computer vision met labels; VLM is taalmodel-finetuning met voorbeeld-promptpairs.

## De stroom

```
Labeling (CVAT / Label Studio)
   ↓ export COCO / JSONL
DVC (dataset-versies)
   ↓
Detector: Ultralytics YOLO  →  mAP per symbool
VLM: LoRA/QLoRA op Qwen-VL
   ↓
MLflow / W&B (runs en metrics)
   ↓
Evaluatie op vaste testset → alleen promoveren zonder regressie
   ↓
Export → vLLM (VLM) + ONNX/TensorRT (detector)
```

## De drie heilige regels

1. **De evaluatieset is nooit trainingsdata.** ±50 tekeningen met gouden antwoorden; ooit gescheiden, altijd apart. Zie [068-evaluatieset](068-evaluatieset.md).
2. **Geen modelversie live zonder regressietest.** Promoveren gebeurt via een gate. Zie [083-cicd](083-cicd.md).
3. **Klantdata alleen met toestemming voor training.** Zie [084-veiligheid-en-avg](084-veiligheid-en-avg.md).

## Wat het onderscheidt van generiek ML-werk

- **Klein domein.** Vijf klassen, herkenbare symbolen, veel herhaling — daardoor haalbaar met weinig data.
- **Data is het probleem, niet de architectuur.** De markt is niet overspoeld met gelabelde Nederlandse installatietekeningen. Verzamelen is de bottleneck.
- **Fouten zijn direct financieel.** Een gemiste WCD betekent tekort materiaal. Daarom meet je niet alleen mAP maar de fout in de materiaallijst. Zie [069-metrics](069-metrics.md).
- **De feedbackloop is de voorsprong.** Correcties uit de review-UI zijn data die concurrenten niet hebben. Zie [070-feedbackloop](070-feedbackloop.md).

## De volgorde waarin je bouwt

1. **Eerst dataset en evaluatieset** — anders kun je niets meten.
2. **Dan een baseline** — YOLO op een kleine set, LoRA op een handvol voorbeelden.
3. **Dan itereren** — meer data, betere labels, groter model.
4. **Dan serving** — vLLM, en de detector in de worker.

De README zet dit ook zo: Fase 0 is "dataverzameling, projectmodel, evaluatieset, baseline". Zie [009-status-en-roadmap](009-status-en-roadmap.md).

## De documenten in deze sectie

| # | Onderwerp |
|---|---|
| 062 | [Basismodel Qwen-VL en licenties](062-basismodel-qwen-vl.md) |
| 063 | [Fine-tuning met LoRA/QLoRA](063-finetuning-lora.md) |
| 064 | [Het detector-trainscript](064-train-detector-script.md) |
| 065 | [YOLO versus RT-DETR](065-symbooldetectie.md) |
| 066 | [Datasetstructuur met DVC](066-datasetstructuur.md) |
| 067 | [Labeling](067-labeling.md) |
| 068 | [De evaluatieset](068-evaluatieset.md) |
| 069 | [Metrics](069-metrics.md) |
| 070 | [De feedbackloop](070-feedbackloop.md) |
| 071 | [Model-serving met vLLM](071-model-serving-vllm.md) |
| 072 | [MLOps en registratie](072-mlops-en-registratie.md) |

## Wat er nu bestaat

[ml/train_detector.py](../ml/train_detector.py) en [ml/finetune_vlm.py](../ml/finetune_vlm.py) zijn **lege bestanden**; [ml/data](../ml/data) en [ml/eval](../ml/eval) zijn lege mappen. Er is geen dataset, geen `.dvc`, geen modelartefact.
