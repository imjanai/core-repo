# 087 — Modellicenties

## De waarschuwing uit de README

> **Modellicentie.** Controleer de licentievoorwaarden van het gekozen Qwen-model voor commercieel gebruik.

En in de tech stack:

> Qwen-VL (fine-tuned; **controleer licentie per modelgrootte**)

Die dubbele vermelding is geen overdreven voorzichtigheid: het is een reëel commercieel risico.

## Waarom per modelgrootte

Qwen publiceert modellen onder verschillende licenties:

| Serie | Voorbeeld | Kenmerk |
|---|---|---|
| Kleine/middelgrote modellen | 0.5B t/m 7B (varieert per release) | Meestal Apache 2.0 — vrij gebruik |
| Grote modellen | 72B en sommige varianten | Vaak een eigen Qwen-licentie met extra voorwaarden |

De grenzen **verschillen per release en per modelserie**. Daarom: lees de licentie van het **exacte** model dat je gaat gebruiken, niet "Qwen in het algemeen".

## Wat je controleert

1. **Commercieel gebruik toegestaan?**
2. **Output mogen gebruiken?** (bijv. trainingsdata-generatie)
3. **Autorisatie vereist?** (sommige licenties vragen om een aanvraag)
4. **Auteursvermelding of notificatieplicht?**
5. **Gebruiksbeperkingen** (defensie, surveillance, enz.) — relevant als je aan bedrijven in bepaalde segmenten levert.

## Wat je vastlegt

- De modelnaam en revisie (`Qwen/Qwen2.5-VL-7B-Instruct`, commit-hash).
- De licentietekst of een link + datum.
- De conclusie: "toegestaan voor commercieel gebruik" met naam van de beoordelaar.

Bewaar dit in een `NOTICE`-bestand of in de documentatie van het ML-pakket. Bij een overname, investering of klantvraag is dat direct beschikbaar.

## Alternatieven als de licentie niet past

| Alternatief | Opmerking |
|---|---|
| Andere Qwen-grootte | Apache-variant kiezen |
| Andere open familie | bv. LLaVA-varianten — afhankelijk van licentie |
| Gesloten API | Geen licentieverhaal, maar dataverwerking bij derden en geen fine-tuning |

Zie [020-keuzes-en-alternatieven](020-keuzes-en-alternatieven.md).

## Wat er nog meer open-source is

Ook de andere libraries hebben licenties; controleer vooral de minder voor de hand liggende:

| Library | Typische licentie | Let op |
|---|---|---|
| Ultralytics YOLO | AGPL-3.0 of enterprise | **AGPL kan verplichten je eigen code open te maken** bij servicelevering — ernstig voor een proprietary product! |
| PaddleOCR | Apache 2.0 | Meestal prima |
| SAHI | MIT | Prima |
| ezdxf | MIT | Prima |
| ifcopenshell | LGPL | Vereist dynamic linking |
| PyMuPDF | AGPL-3.0 of commercieel | **Zelfde risico als Ultralytics** |

**De Ultralytics- en PyMuPDF-licenties verdienen expliciete aandacht**: AGPL kan betekenen dat een SaaS-dienst die ze gebruikt, de eigen broncode beschikbaar moet stellen — of dat je een commerciële licentie koopt. Bespreek dit met een jurist vóór Fase 1. Zie [099-open-vragen](099-open-vragen.md).

## Wat er nu bestaat

Niets aan vastgelegd. `pyproject.toml` bevat alleen de naam van de packages, niet hun licentieconclusies.
