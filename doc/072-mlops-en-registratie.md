# 072 — MLOps en registratie

## De vraag

Welk model draait er nu, hoe is het gemaakt, en hoe keren we terug als het slechter blijkt?

## De onderdelen

| Onderdeel | Wat | Waarom |
|---|---|---|
| **MLflow** of **Weights & Biases** | Runs, metrics, artefacten | Reproduceerbaarheid en vergelijking |
| **DVC** | Datasetversies | "Trainen op revisie X" |
| **Promotiegate** | Evaluatieset vóór publicatie | Geen regressie in productie |
| **Modelregistry** | Welk model draait waar | Herleidbaarheid per analyse |

## Wat er per run wordt vastgelegd

```python
mlflow.log_params({
    "basismodel": "Qwen2.5-VL-7B-Instruct",
    "method": "qlora",
    "rank": 16,
    "epochs": 3,
    "dataset_revisie": "a3f2c1",
    "seed": 42,
})
mlflow.log_metrics({
    "map50": 0.871,
    "recall": 0.912,
    "tellingfout": 1.4,
    "kostenfout_pct": 1.8,
})
mlflow.log_artifact("eval-rapport.md")
```

Zonder deze logging is een resultaat na drie weken niet te reproduceren — en is elke discussie over "welk model was beter?" een meningsverschil.

## De promotiegate

```
kandidaat-model
      ↓
evaluatie op ml/data/golden
      ↓
┌───────────────────────────────────┐
│ geen regressie op enige metric?   │
└───────────────────────────────────┘
   ├─ ja  → registratie als "staging" → canary → "production"
   └─ nee → afwijzing met rapport
```

Concreet in CI:

```bash
uv run python ml/eval/run_eval.py --model kandidaat --baseline huidig
```

Dat commando staat al in de README onder "Testen en kwaliteit" — maar [ml/eval](../ml/eval) bestaat nog niet.

## Herleidbaarheid per analyse

Sla in het project-record op **welk modelversie** elke stap uitvoerde:

```python
class StapLog(BaseModel):
    project_id: str
    stap: str
    model_versie: str
    tijdstip: datetime
```

Zo kun je achteraf zeggen: "deze analyse is gemaakt met elektro-vl-v0.3" — onmisbaar bij klachten en bij het evalueren van nieuwe versies op oud werk.

## Wat DVC en MLflow niet doen

Ze bewaken niet of je dataset wel netjes is. Dat doe je met:

- een splitsingsbestand dat per project vastlegt in welke set het valt ([066](066-datasetstructuur.md)),
- een check in de trainer die `golden/` uitsluit,
- reviews op labelkwaliteit ([067](067-labeling.md)).

## Wat er nu bestaat

`mlflow` staat in [pyproject.toml](../pyproject.toml); er is geen run, geen registratie, geen remote. [ml/eval](../ml/eval) is leeg.
