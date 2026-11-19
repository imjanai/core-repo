# Evaluatierapport: elektro-vl
**Dataset:** golden_v1

## Niveau 1 — Detectie (Raster & VLM)
- **mAP@50:** 0.885
- **mAP@50-95:** 0.742
- **Precisie:** 0.912
- **Recall:** 0.894

| Symboolklasse | mAP@50 | Precisie | Recall |
|---|---|---|---|
| wandcontactdoos | 0.910 | 0.920 | 0.915 |
| schakelaar | 0.845 | 0.880 | 0.820 |
| lichtpunt | 0.932 | 0.940 | 0.930 |
| datapunt | 0.860 | 0.890 | 0.840 |
| verdeler | 0.980 | 0.990 | 0.970 |

## Niveau 2 — Telling per tekening
- **Gemiddelde tellingfout:** 20.67 symbolen/tekening
- **Perfecte tekeningen (fout = 0):** 0.0% (0/6)

## Niveau 3 — Uitkomst (Materiaallijst & Kosten)
- **Gemiddelde materiaalkostenfout:** € 297.90
- **Kostenafwijking percentage:** 59.56%
- **Totale grondwaarde:** € 2994.81 | **Voorspeld:** € 1207.41

## Niveau 4 — Doorlaat (Review-UI)
- **Tekeningen zonder correctie:** 0.0%
- **Gemiddeld aantal correcties per tekening:** 20.67

---
### Promotiebesluit: [FAIL] AFGEKEURD

**Afwijzingsredenen:**
- Level 2: Tellingfout (20.67) > drempel (1.50)
- Level 3: Kostenfout (59.56%) > drempel (2.50%)
