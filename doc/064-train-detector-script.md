# 064 — Wat `ml/train_detector.py` moet doen

## De huidige staat

```python
# ml/train_detector.py   — leeg bestand
```

Dit document beschrijft wat erin komt.

## De opzet

```python
"""Train de symbooldetector op de gelabelde dataset."""
from ultralytics import YOLO

def main(config_pad: str = "ml/config/detector.yaml"):
    config = laad_config(config_pad)

    model = YOLO(config.basismodel)          # bv. "yolo11n.pt"

    model.train(
        data=config.dataset_pad,             # YAML met klassen + paden
        epochs=config.epochs,
        imgsz=config.imgsz,                  # bv. 1024 (tegel-grootte)
        batch=config.batch,
        project="runs/detector",
        name=config.naam,
        seed=config.seed,
    )

    resultaten = model.val()
    log_metrics(resultaten)                  # MLflow of W&B

if __name__ == "__main__":
    main()
```

## De dataset-YAML

```yaml
path: ml/data/detector
train: images/train
val: images/val
names:
  0: wandcontactdoos
  1: schakelaar
  2: lichtpunt
  3: datapunt
  4: verdeler
```

De klassen komen overeen met `SymbolType` — zie [025-symboltype-enum](025-symboltype-enum.md). **Houd die twee synchroon**: een extra klasse in het schema zonder hertraining betekent een detector die het type nooit voorspelt.

## Wat het script nog moet doen

### 1. Reproduceerbaarheid

```python
seed=42
```

Plus: de datasetversie vastleggen (DVC-revisie) en de config meeloggen. Zie [072-mlops-en-registratie](072-mlops-en-registratie.md).

### 2. Splitsing bewaken

De splitsing train/val moet **per tekening** zijn, niet per tegel. Anders lekt dezelfde tekening in tegels naar beide kanten en lijkt de evaluatie veel beter dan de werkelijkheid. Zie [068-evaluatieset](068-evaluatieset.md#data-leakage).

### 3. Metrics loggen

- mAP@50 en mAP@50-95 per klasse,
- precisie en recall op de drempel die de pipeline gebruikt,
- een handvol visuele resultaten voor review door een domeinexpert.

### 4. Export

Na validatie exporteren naar ONNX (of direct de `.pt` gebruiken in de worker). Zie [045-vision-detector](045-vision-detector.md#exporteren-voor-productie).

### 5. Promoveren of niet

```python
if resultaten.mAP50 < huidige_productiemodel.mAP50:
    raise SystemExit("Regressie: niet promoveren")
```

Deze check hoort idealiter in CI, niet alleen in het script. Zie [083-cicd](083-cicd.md).

## De invoer die je nodig hebt

| Bestand | Vorm |
|---|---|
| `ml/data/detector/images/{train,val}/*.png` | Tegels of hele pagina's |
| `ml/data/detector/labels/{train,val}/*.txt` | YOLO-formaat: klasse x_center y_center w h (genormaliseerd) |

De conversie van CVAT/Label Studio naar YOLO-formaat gebeurt bij het exporteren. Zie [067-labeling](067-labeling.md) en [066-datasetstructuur](066-datasetstructuur.md).

## Hoe je begint

1. Verzamel 20–50 tekeningen.
2. Label ze volledig (niet steekproefsgewijs).
3. Splits per tekening.
4. Train een baseline (`yolo11n`, 50 epochs).
5. Noteer mAP als nulmeting — dát is de baseline waar elke verbetering tegen wordt afgezet.
