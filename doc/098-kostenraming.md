# 098 — Kostenraming

Een eerste orde-geschatte raming. **Geen garantie**: de werkelijke cijfers hangen af van gebruik, regio en keuzes die nog niet gevallen zijn. Het doel is de posten zichtbaar maken.

## De posten

### 1. Infrastructuur

| Item | Indicatie | Opmerking |
|---|---|---|
| GPU-instance (L4/A10-class) | € 500–1.500 / maand | Voor vLLM; hangt af van volume |
| CPU-servers (API, worker) | € 100–400 / maand | 2–4 instances |
| PostgreSQL (managed) | € 50–200 / maand | Met backups |
| Redis | € 20–80 / maand | |
| Objectopslag | € 10–100 / maand | Hangt af van tekeningen |
| Observability | € 50–200 / maand | Sentry, Langfuse |

**Totaal infra:** grofweg € 700–2.500 / maand bij bescheiden gebruik.

### 2. Ontwikkeling

| Rol | Indicatie |
|---|---|
| ML-ingenieur | € 8.000–15.000 / maand |
| Backend | € 8.000–15.000 / maand |
| Frontend | € 7.000–13.000 / maand |
| Domeinexpert (deeltijd) | € 3.000–6.000 / maand |

Dit is veruit de grootste post — en de reden waarom de MVP klein moet zijn.

### 3. Datakosten

| Post | Indicatie |
|---|---|
| Labeling 100 tekeningen | € 3.000–10.000 (of interne uren) |
| Gouden set 50 tekeningen | € 5.000–15.000 |
| Hertraining per maand | GPU-uren, klein |

### 4. Juridisch en compliance

| Post | Indicatie |
|---|---|
| Licentiebeoordeling modellen | Eenmalig |
| AVG-advies, DPA's | Eenmalig + jaarlijks |
| Pentest | € 5.000–15.000 eenmalig |

## Wat de klant kost om te draaien

Per analyse draait een GPU-seconden-aantal. Bij 60 s GPU-tijd op een instance van ~€ 1,50/uur: enkele centen per tekening aan directe kosten. **Dat is gunstig** — de marge zit in de waarde, niet in de kosten.

## Waar de marge heen gaat

```
opbrengst per analyse
  − directe GPU-kosten      (centen)
  − opslag                  (centen)
  − onderhoud en support   (de echte kosten)
  = marge
```

## Waar het mis kan lopen

| Risico | Gevolg | Beperking |
|---|---|---|
| GPU veel gebruikt door VLM | Kosten pieken | Crops begrenzen, caching |
| Te dure modelgrootte | Onrendabel | Klein model waar het kan |
| Te veel handwerk in onboarding | Marge weg | Sjablonen, automatisering |
| Retentie laag | Waarde per klant laag | Integraties, workflows |

## Wat er nu bestaat

Geen facturen, geen metingen. Deze raming is een aannames-document, geen inzicht.
