# Evaluatierapport: opencv-baseline
**Dataset:** 8fdf3f15de5d8f6ca963cc42dee88f4712cb7f05b3a0bb48eecd517981eeee2a

- **Rastertolerantie (px):** 12.0
- **Vectortolerantie (mm):** 100.0
- **Detectorbestand:** geen
- **Detector SHA-256:** geen
- **VLM aangevraagd:** False
- **VLM-model:** uit

## Niveau 1 — Symboolpositie en type
Een match vereist hetzelfde symbooltype en een positie binnen de ingestelde afstand.
- **Precisie:** 0.364
- **Recall:** 0.438
- **F1:** 0.397

| Symboolklasse | Verwacht | Voorspeld | Juist | Precisie | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| datapunt | 36 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| lichtpunt | 38 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| schakelaar | 24 | 116 | 24 | 0.207 | 1.000 | 0.343 |
| verdeler | 6 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| wandcontactdoos | 40 | 57 | 39 | 0.684 | 0.975 | 0.804 |

### Fouten per tekening

| Tekening | Juist | Gemist | Valse detecties | Verkeerd type | Detector | VLM |
|---|---:|---:|---:|---:|---|---|
| synth-golden-001.png | 12 | 0 | 7 | 12 | heuristic_cv | disabled |
| synth-golden-002.png | 9 | 1 | 6 | 14 | heuristic_cv | disabled |
| synth-golden-003.png | 8 | 2 | 6 | 14 | heuristic_cv | disabled |
| synth-golden-004.png | 9 | 2 | 5 | 13 | heuristic_cv | disabled |
| synth-golden-005.png | 13 | 1 | 6 | 10 | heuristic_cv | disabled |
| synth-golden-006.png | 12 | 1 | 6 | 11 | heuristic_cv | disabled |

## Niveau 2 — Telling per tekening
- **Gemiddelde tellingfout:** 31.50 symbolen/tekening
- **Perfecte tekeningen (fout = 0):** 0.0% (0/6)

## Niveau 3 — Uitkomst (Materiaallijst & Kosten)
- **Gemiddelde materiaalkostenfout:** € 184.26
- **Kostenafwijking percentage:** 36.80%
- **Totale grondwaarde:** € 2994.81 | **Voorspeld:** € 1889.26

## Niveau 4 — Geschatte reviewcorrecties
- **Tekeningen zonder correctie:** 0.0%
- **Gemiddeld aantal correcties per tekening:** 19.50

---
### Promotiebesluit: [FAIL] AFGEKEURD

**Afwijzingsredenen:**
- Symbool-F1 (0.397) < drempel (0.850)
- Level 2: Tellingfout (31.50) > drempel (1.50)
- Level 3: Kostenfout (36.80%) > drempel (2.50%)

## Experiment met rasterclassificatie en tegeldetectie

Evaluatie op dezelfde zes synthetische golden tekeningen, met OpenCV als
kandidaatdetector. De classifier is getraind op 2.114 crops uit 24 apart
gegenereerde tekeningen, inclusief achtergrondcrops. De classifierdrempel
was 0,65. Tegels waren 512 px breed met 96 px overlap.

| Configuratie | F1 | Juiste matches | Verkeerd type |
|---|---:|---:|---:|
| OpenCV, volledige afbeelding | 0,397 | 63 | 74 |
| OpenCV en classifier | 0,961 | 135 | 2 |
| OpenCV met tegels | 0,397 | 63 | 74 |
| OpenCV met tegels en classifier | 0,961 | 135 | 2 |

De classifier haalde de symbool-F1-drempel. De gemiddelde tellingfout van
1,83 en de kostenafwijking van 32,87% overschreden de promotiedrempels. De
score is gemeten op synthetische tekeningen. Er is in dit experiment geen
YOLO-checkpoint, VLM of praktijkdataset gebruikt.
