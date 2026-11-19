# 090 — Foutscenario's en herstel

## De houding

> Verwacht dat er iets misgaat. Ontwerp zodat de gebruiker het begrijpt en het systeem herstelt.

## De catalogus

### Upload

| Fout | Gebruiker ziet | Systeem doet |
|---|---|---|
| Bestand te groot | "Dit bestand is X MB, maximaal Y" | 413 |
| Onbekend formaat | "Ondersteund: DXF, DWG, IFC, PDF, PNG, JPG" | 415 |
| Beveiligd PDF | "Dit PDF is beveiligd met een wachtwoord" | Fout in stap 2/3 |
| Corrupte DXF | "Dit DXF-bestand is niet leesbaar" | Fout in stap 4a |
| S3 onbereikbaar | "Tijdelijk niet beschikbaar, probeer opnieuw" | Retry, daarna fout |

### Pipeline

| Fout | Herstel |
|---|---|
| Taak-timeout | Retry met backoff, daarna `failed` |
| GPU onbereikbaar | Taak terug in de queue; alarm naar monitoring |
| VLM geeft ongeldige JSON | Eén herhaling met fout in de prompt; daarna overslaan |
| Detectie levert niets | Waarschuwing: "geen symbolen herkend — controleer of de tekening leesbaar is" |
| Schaal niet bepaald | Waarschuwing: "schaal geschat; controleer de materiaallengtes" |
| Worker-crash | Taak opnieuw; dankzij idempotentie geen dubbele data |

### Output

| Fout | Herstel |
|---|---|
| Excel-export faalt | Melding; PDF-export werkt nog |
| DXF-export faalt | Melding; Excel en PDF werken nog |
| Offerte-template mist | Fout naar support; analyse blijft beschikbaar |

## De drie principes

### 1. Begrijpelijk, niet technisch

> "Dit PDF-bestand is beveiligd met een wachtwoord"

niet

> `PyMuPDFError: cannot open encrypted document`

Log de technische fout wel — naar Sentry met `trace_id`. Zie [080-observability](080-observability.md).

### 2. Hervatten bij de laatste stap

Elk tussenresultaat staat in S3. Een herstart draait alleen de mislukte stap. Zie [015-dataflow-eind-tot-eind](015-dataflow-eind-tot-eind.md).

### 3. Deeluitval is geen totaaluitval

Als de detectie niets oplevert maar de vector-parser wel, levert de analyse alsnog een bruikbaar resultaat, met een waarschuwing. Alleen als alle sporen falen, faalt het project.

## Rampscenario's

| Scenario | Impact | Herstel |
|---|---|---|
| Database kwijt | Alle projecten | Restore uit backup; PITR |
| S3-objecten kwijt | Bronbestanden | Restore uit backup; replica |
| GPU kapot | Geen analyses | CPU-pad of vervangende instance |
| Datalek | Vertrouwen | Melding, analyse, communicatie |
| Verkeerd model in productie | Foute materiaallijsten | Terugrollen naar vorige versie (registratie maakt dat mogelijk) |

Zie [072-mlops-en-registratie](072-mlops-en-registratie.md) voor de herleidbaarheid per analyse.

## Wat er nu bestaat

Niets. Er is geen foutafhandeling omdat er geen code is.
