# 101 — De trainingspipeline (geïmplementeerd)

Dit document beschrijft wat er **nu staat** in `ml/`: de trainingspipeline
voor detector en VLM, de evaluatiegate en de data-guards. Het sluit aan op
[061-ml-overview](061-ml-overview.md) (ontwerp) en [072-mlops-en-registratie](072-mlops-en-registratie.md)
(registratie) — die beschreven het plan; dit document beschrijft de uitvoering.

## De kaart

```
Labeling (CVAT / Label Studio) → COCO / JSONL
        ↓
ml/dataset.py — splitsen per tekening, golden-guard (doc/066/068)
        ↓
┌──────────────────────────────┬──────────────────────────────┐
│ ml/train_detector.py         │ ml/finetune_vlm.py           │
│ YOLO (ultralytics)           │ LoRA/QLoRA op Qwen-VL        │
│ ml/config/detector.yaml      │ ml/config/vlm.yaml           │
└──────────────┬───────────────┴──────────────┬───────────────┘
               ↓ combinatie van beiden        ↓
        ml/eval/run_eval.py — vier niveaus + promotiegate (doc/069)
               ↓
        Rapport (markdown + metrics-JSON) → promoveren of afwijzen
```

## Bestanden

| Bestand | Rol |
|---|---|
| `ml/dataset.py` | Gedeelde hulpjes: afbeeldingen/labels vinden, per-tekening splitsen, `splitsing.yaml` schrijven/lezen, **golden-guard** |
| `ml/config/detector.yaml` | YOLO-config: basis, `imgsz=1024`, seed, export, MLflow, promotiedrempel |
| `ml/config/vlm.yaml` | Qwen-VL + LoRA-config: model, rank, epochs, dataset-paden |
| `ml/train_detector.py` | detector-trainscript: dataset-checks → train → val → MLflow → ONNX → gate |
| `ml/finetune_vlm.py` | VLM fine-tunescript: JSONL valideren → Qwen-VL + LoRA → adapter opslaan |
| `ml/eval/run_eval.py` | Evaluatieset: 4 niveaus metrics + regressiegate + rapport |
| `tests/ml/test_dataset.py` | Splitsing, golden-guard, determinisme (28 tests samen met test_eval) |
| `tests/ml/test_eval.py` | IoU, precisie/recall, telling, materiaalfout, doorlaat, regressie |

## De drie heilige regels, technisch afgedwongen

1. **`golden/` nooit trainingsdata** — `ml.dataset.ensure_no_golden()` wordt
   aangeroepen vóór het laden in beide trainers; de eval-script-lezer vereist
   juíst dat de gouden antwoorden *uit* `golden/` komen.
2. **Splitsen per tekening** — `make_split()` groepeert op projectmap en
   verdeelt tekeningen, nooit tegels. Deterministisch met vaste `seed`
   (default 42), controversieel genoeg voor reproduceerbaarheid.
3. **Meettekeningen** — `splitsing.yaml` is deterministisch, wegschrijfbaar
   en vergelijkbaar; every model-versie draait op dezelfde set.

## De promotiegate

`run_eval.py` exit 1 bij regressie op **enige** metric (doc/069):

```bash
uv run python ml/eval/run_eval.py --model kandidaat --baseline production
```

- hoger-is-beter metrics (map50, recall, doorlaat, perfecte tekeningen):
  kandidaat moet `>=` baseline zijn;
- bij een lager-is-better metric (`kostenfout_pct` wordt momenteel als
  hoger-is-beter gemeten; TODO: expliciete richting per metric):

Dat TODO is bewust zichtbaar: de gate mag niet stilletjes een richting
aannemen zonder het vast te leggen.

## Hoe je het gebruikt

### 1. Detector (GPU-runner)

```bash
# Dataset klaar (doc/066/067): ml/data/detector/images/{train,val}, labels
uv run python ml/train_detector.py ml/config/detector.yaml
```

Het script:

1. controleert de dataset-YAML en de inventory,
2. schrijft `ml/data/splitsing.yaml` per tekening,
3. Blokkeert golden-leakage harde stop,
4. traint met `yolo11n`, `imgsz=1024`, seed 42,
5. valideert en logt mAP@50 / mAP@50-95 naar MLflow,
6. exporteert naar ONNX (optioneel, faalt door),
7. past de promotie-drempel toe.

### 2. VLM (GPU-runner)

```bash
# JSONL klaar (doc/063/066): image / question / answer
uv run python ml/finetune_vlm.py ml/config/vlm.yaml
```

Valideert elk JSONL-voorbeeld vóór het trainen (image/question/answer
verblijvend; geen golden in de data) en traint met LoRA (rank 16, alpha 32)
op `Qwen2.5-VL-7B-Instruct`. De adapter komt in `runs/vlm/adapter/`.

### 3. Evaluatie (elke kandidaat-versie)

```bash
uv run python ml/eval/run_eval.py --model elektro-vl-v0.1 --baseline ml/eval/production.json
```

Leest `ml/data/golden/antwoorden/{voorspeld,gouden,prijzen}.json`, berekent
de vier niveaus, schrijft `ml/eval/rapport.md` + `rapport.json`, en exit 1
bij regressie.

## Wat er nog ontbreekt (Fase 0 blijft open)

| Gat | Oplossing | Waar |
|---|---|---|
| Geen echte dataset | 20–50 tekeningen verzamelen + labelen | [067](067-labeling.md) |
| DVC niet geïnitieerd | `dvc init` + remote | [066](066-datasetstructuur.md) |
| Voorspellingen nog niet uit de worker | eval leest nu JSON In; worker levert `voorspeld.json` aan (doc/040 stappen 4–8) | [083](083-cicd.md) |
| Baseline metrics ontbreken | na de eerste run registreren als `production.json` | [072](072-mlops-en-registratie.md) |
| CI-promotiegate niet geautomatiseerd | `.github/workflows/model-eval.yml` (GPU-runner) | [083](083-cicd.md) |
| Richting per metric in de gate | hoger-is-beter is nu impliciet | zie hierboven |
