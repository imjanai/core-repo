# Modelbenchmark

Voer de volledige tekeningenpipeline uit op gekoppelde tekeningen en handmatig
gecontroleerde antwoorden.

```sh
uv run python ml/eval/run_eval.py --dataset ml/data/golden --report eval-rapport.md --metrics-json eval-metrics.json
```

Voor een getrainde detector voeg je `--detector-weights <checkpoint.pt>` toe.
Met `--enable-vlm` schakel je de geconfigureerde vLLM-service in. Het rapport
vermeldt het checkpoint, de SHA-256 en de detector- en VLM-status per tekening.
Zonder checkpoint kan de pipeline op OpenCV-heuristieken terugvallen.

- Zet originele tekeningen in `tekeningen/` en bijbehorende Project-JSON in
  `antwoorden/`, met dezelfde bestandsstam. Houd alle revisies van een project
  samen in één split. Gebruik praktijktekeningen die nooit voor training of
  modelkeuze zijn gebruikt om de uiteindelijke kwaliteit te meten.
- Rasterannotaties gebruiken dezelfde gekalibreerde coördinaten als de detector.
  `Project.scale` geeft millimeters per pixel aan. Vectorannotaties staan in mm.
- Precisie, recall en F1 tellen één-op-één matches van hetzelfde type binnen
  de tolerantie in `ml/config/eval.yaml`. De resterende symbolen geven gemiste
  symbolen, valse detecties en verwisselde types. De JSON bevat hun posities.
  Deze puntmeting vereist geen bounding boxes.
- Gebruik `--baseline eval-metrics.json --gate` met een vorige JSON om de
  F1-score op dezelfde tekeningen en tolerantie te vergelijken. Een mislukte
  gate geeft exitcode 1.

## Trainingscrops uit gecontroleerde tekeningen

Maak buiten de repository een manifest met rastertekeningen en gecontroleerde
Project-JSON. Verwijs naar alle revisies van hetzelfde werk met dezelfde
`project_family`. Vermeld de families uit de golden set in `golden_families`,
ook wanneer hun bestanden buiten dit manifest staan. Gebruik alleen lokaal
beschikbare, geanonimiseerde tekeningen met toestemming voor training.

```json
{
  "golden_families": ["pilot-07"],
  "drawings": [
    {
      "drawing": "werk-01-rev-a.png",
      "reviewed": "werk-01-rev-a.reviewed.json",
      "project_family": "werk-01",
      "allow_training": true
    }
  ]
}
```

```sh
uv run python -m ml.feedback.export_crops manifest.json ../training-crops
```

De export bevat gelabelde symboolcrops en JSONL voor classificatie en VLM.
De train/validatiesplit is deterministisch per projectfamilie. Golden families
en tekeningen zonder toestemming worden uitgesloten. De export maakt geen
bounding boxes voor detectortraining.

## Classifier and tiled detection experiments

Export reviewed raster crops as above and add verified background examples
to each training drawing's manifest entry via `"background_px": [[x, y]]`.
Use pixel coordinates for background centers. Background crops must have
no annotated symbol center inside the crop. The classifier uses the training
split only and accepts matching square crops. Start with `--crop-size 48`
for symbols around 24 px wide and adjust for your drawing resolution.

```sh
uv run python -m ml.feedback.export_crops manifest.json ../training-crops --crop-size 48
uv run python -m ml.train_classifier ../training-crops ../symbols.npz
uv run python ml/eval/run_eval.py --dataset ../pilot-golden --classifier ../symbols.npz --report classifier.md --metrics-json classifier.json
uv run python ml/eval/run_eval.py --dataset ../pilot-golden --tiled --tile-size 512 --tile-overlap 96 --report tiled.md --metrics-json tiled.json
```

Evaluate a baseline on the same drawings without either switch. To test both
changes together, pass both switches. The classifier runs on raster detector
candidates after fusion. It keeps their positions, sets uncertain types to
`onbekend`, and removes confident background predictions. Its confidence is
a weighted neighbour vote, not a calibrated probability. Tiled detection
projects tile detections back to full-image coordinates and suppresses
overlapping duplicates.

For a synthetic smoke experiment, run
`uv run python -m ml.data.synthetic_classifier ../synthetic-classifier`.
It trains on separate generated drawings and writes `classifier.npz`.
Keep the benchmark drawings out of the training crop manifest.

In the worker, opt in via `SYMBOL_CLASSIFIER_PATH` and
`SYMBOL_CLASSIFIER_THRESHOLD` (default 0.65), or `DETECTOR_TILED=1` for tiling
with the pipeline's default tile size and overlap.
