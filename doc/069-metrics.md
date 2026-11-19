# 069 — Metrics

## Waarom meerdere lagen

Eén cijfer is nooit genoeg. imjan AI rapporteert op vier niveaus, van technisch naar commercieel:

```
mAP  →  telling  →  materiaallijst  →  review-doorlaat
```

Elk niveau zegt iets anders, en alleen het laatste is wat de klant voelt.

## Niveau 1 — Detectie

| Metric | Wat het zegt |
|---|---|
| **mAP@50** | Gemiddelde precisie bij IoU 0.5 — "wordt het object gevonden?" |
| **mAP@50-95** | Strakker — "wordt de box ook nauwkeurig?" |
| **Precisie** | Hoeveel gevonden objecten zijn echt? |
| **Recall** | Hoeveel echte objecten zijn gevonden? |
| **Per klasse** | Verbergt de gemiddelde geen slechte klasse |

**Aandacht:** bij symbolen is **recall belangrijker dan precisie** voor de vakman — een gemist punt is duurder dan een kandidaat die weggeklikt wordt. Maar te lage precisie maakt de review onaantrekkelijk. Zie de drempelkeuze in [036-stap-4b-detectie](036-stap-4b-detectie.md).

## Niveau 2 — Telling

| Metric | Berekening |
|---|---|
| **Tellingfout per klasse** | `|voorspeld − grondwaarde|` per tekening |
| **Totale tellingfout** | Som over klassen |
| **Perfecte tekeningen** | Percentage tekeningen met fout 0 |

Dit is een betere maatstaf dan mAP voor de materiaallijst: 5 gemiste symbolen op locatie X maar wel geteld in het totaal is financieel minder erg dan 5 symbolen die ontbreken.

## Niveau 3 — Uitkomst (het belangrijkste)

| Metric | Wat het zegt |
|---|---|
| **Materiaallijst-fout (aantal)** | `|lijst_aantal − gouden_aantal|` per artikel |
| **Materiaallijst-fout (kosten)** | Bedrag dat er naast zit, in euro's |
| **Kostenfout als percentage** | Van de totale materiaalsom |
| **Waarschuwingen: terecht / vals** | Kwaliteit van de regelengine |

Dit is de metric die je aan een klant laat zien:

> "De gemiddelde afwijking op de materiaalsom is 1,8%."

Dat is een claim die verkoopbaar én meetbaar is.

## Niveau 4 — Doorlaat

| Metric | Wat het zegt |
|---|---|
| **% tekeningen zonder correctie** | Directe tijdwinst |
| **Gemiddeld aantal correcties per tekening** | Workload van de vakman |
| **Tijd per tekening in de review** | Praktijkmeting bij pilotklanten |

Dit meet de echte workflow — en het is de ROI-maatstaf uit [005-waardepropositie](005-waardepropositie.md).

## Hoe rapporteren

Per modelversie een vast rapport:

```markdown
## Modelversie elektro-vl v0.3 — 2026-10-12
Dataset: ml/data/golden @ a3f2c1

Detectie (rasterpad):
  mAP@50:      0.871   (was 0.844)
  recall:      0.912   (was 0.889)
  per klasse:  WCD 0.90, schakelaar 0.78, lichtpunt 0.93, ...

Telling:
  gem. tellingfout: 1.4 symbolen/tekening  (was 2.1)
  perfecte tek.:    58%                   (was 41%)

Uitkomst:
  materiaalkostenfout: 1.8% gemiddeld     (was 2.6%)

Doorlaat:
  % zonder correctie: 46%                 (was 33%)

Promoveren: JA (geen regressie op enige metric)
```

## Waar je fout kunt gaan

| Fout | Gevolg |
|---|---|
| Alleen mAP rapporteren | Misschien goed model, slechte materiaallijst |
| Gemiddelden zonder spreiding | Eén desastreuze tekening verdwijnt |
| Vergelijken tegen een andere set | Cijfers niet vergelijkbaar |
| Metrics na tune-iteraties opnieuw kiezen | Selectie-bias |

## Wat er nu bestaat

Niets. Er is geen evaluatieset en geen [ml/eval/run_eval.py](../ml/eval) — terwijl de README die aanroept als `uv run python ml/eval/run_eval.py --model elektro-vl`.
