# 005 — Waarom zou iemand hiervoor betalen?

## De belofte

> Van tekening naar gecontroleerde materiaallijst en offerte — zonder uren handwerk, zonder dat er iets over het hoofd wordt gezien.

## Rekenvoorbeeld

Stel een calculator maakt 8 offertes per week en besteedt gemiddeld 2 uur per offerte aan uittellen en intypen: **16 uur/week**.

| Scenario | Uren | Effect |
|---|---|---|
| Nu | 16 u/wk | Volledig handmatig |
| Met imjan, 70% automatisch | 4,8 u/wk | 11,2 uur vrij |
| Besparing per maand | ±45 uur | Ruimte voor meer aanbestedingen |

En dat zonder de kosten mee te rekenen van een gemiste doos of een verkeerde prijs — die zitten doorgaans in de marge.

## Waarde per doelgroep

| Doelgroep | Primair voordeel | Type waarde |
|---|---|---|
| Elektricien / zzp'er | Minder avonduren aan offertes | Tijd |
| Calculator | Consistentere inschatting | Marge |
| Werkvoorbereider | Materiaal klopt bij levering | Minder faalkosten |
| Tekenaar | AI zet eerste versie neer via MCP | Tijd |
| Directie | Herhaalbaar proces, minder afhankelijk van één senior | Schaal |

## Waarom nu

1. **Vision-language modellen kunnen nu** wat ze twee jaar geleden niet konden: tekeningen interpreteren in plaats van beschrijven.
2. **Vectorformaten worden onderschat** — DXF/IFC bevatten de waarheid al, niemand benut ze op deze manier.
3. **Gegevensborging** — correcties worden automatisch trainingsdata, dus het systeem wordt per klant beter ([070-feedbackloop](070-feedbackloop.md)). Dat is een doodlopende voorsprong voor wie er als eerste mee werkt.

## Waarom geen generieke AI

| Eigenschap | Generieke LLM | imjan AI |
|---|---|---|
| Telt betrouwbaar | ❌ hallucineert | ✅ code telt |
| Kent NEN 1010 | ❌ niet specifiek | ✅ regelengine |
| Maakt geldige DXF | ❌ plaatjes | ✅ ezdxf via MCP |
| Beter met eigen data | ❌ algemeen | ✅ fine-tune + feedback |
| Verantwoordelijkheid | onduidelijk | ✅ mens beslist |

## Het verkoopargument in één zin

> "Uw calculator doet het werk dat een computer beter kan — en houdt tijd over voor het werk dat alleen een mens kan."

## Waar de waarde moet worden bewezen

De ROI-claims hierboven zijn een model. Ze moeten geverifieerd worden met de pilotklanten uit Fase 1; de meting daarvoor is het **percentage tekeningen dat zonder correctie door de review komt** (zie [069-metrics](069-metrics.md)). Vanaf dat moment is het geen belofte maar een cijfer.
