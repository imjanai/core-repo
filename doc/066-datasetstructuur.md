# 066 — Datasetstructuur

## De basis

De README:

> `ml/data/` — DVC-gebeheerd

**DVC (Data Version Control)** bewaart grote bestanden buiten git maar houdt versies bij, net als git doet voor code. Zo kun je reproduceren: "trainen op revisie `a3f2c1` van de dataset".

## De mappenindeling

```
ml/data/
├── .dvc/                     # DVC-metadata
├── raw/                      # onbewerkte tekeningen (per klant, geanonimiseerd)
│   └── project-001/
│       ├── bron.dxf
│       └── pagina-01.png
├── detector/                 # YOLO-formaat voor de detector
│   ├── images/
│   │   ├── train/
│   │   └── val/
│   └── labels/
│       ├── train/            # klasse x_center y_center w h
│       └── val/
├── vlm/                      # JSONL voor de VLM
│   ├── train.jsonl
│   └── val.jsonl
├── golden/                   # DE EVALUATIESET — nooit in train/val
│   ├── tekeningen/
│   └── antwoorden/
└── splitsing.yaml            # welk project in welke splitsing
```

## Twee formaten, twee modellen

### Detector: YOLO-formaat

```
# labels/train/001.txt
0 0.5231 0.4412 0.0121 0.0189
2 0.5312 0.4495 0.0119 0.0185
```

Per regel: klasse, ge-normaliseerd middelpunt, ge-normaliseerde breedte en hoogte.

### VLM: JSONL

```json
{"image": "pagina_012.png",
 "question": "Welke ruimtes ziet u? Geef JSON met naam en polygoon.",
 "answer": "[{\"name\": \"Woonkamer\", \"polygon\": [[120,80],[400,80],[400,300],[120,300]]}]"}
```

Zie [063-finetuning-lora](063-finetuning-lora.md) voor de verwerking.

## De splitsing

**Per tekening splitsen, nooit per tegel of per symbool.** Anders lekt dezelfde tekening in tegels naar zowel train als val en lijkt de prestatie veel beter dan de werkelijkheid. Zie [068-evaluatieset#data-leakage](068-evaluatieset.md#data-leakage).

`splitsing.yaml` legt vast welk project in welke splitsing zit — deterministisch, deelbaar, controlegbaar.

## Wat er geanonimiseerd moet worden

Tekeningen bevatten vaak:

- projectnamen en adresgegevens in de titelblok,
- namen van opdrachtgevers,
- soms tekeningen van woonhuizen met adres.

**Vóór opslag in `raw/`:** titelblokken wegpoetsen of vervangen. Niet achteraf — geanonimiseerde data mag niet terug te herleiden zijn. Zie [084-veiligheid-en-avg](084-veiligheid-en-avg.md).

## Hoe DVC werkt in de praktijk

```bash
uv run dvc init
uv run dvc add ml/data/detector
uv run git add ml/data/detector.dvc .dvc/
uv run git commit -m "data: detectorset v1"

# later, reproduceren
uv run dvc pull ml/data/detector
```

De bestanden gaan naar een remote (S3 of DVC-remote); de repo houdt alleen hashes bij.

## De heilige regel

`ml/data/golden/` gaat **nooit** naar `train/` of `val/`. De evaluatieset is de promoveerbaarheidsmaatstaf; als erop getraind wordt, is elke meting waardeloos. Zie [068-evaluatieset](068-evaluatieset.md).

## Wat er nu bestaat

[ml/data](../ml/data) is leeg; er is geen `.dvc` en geen remote geconfigureerd.
