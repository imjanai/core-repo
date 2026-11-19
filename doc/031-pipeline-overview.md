# 031 — De pipeline: tien stappen

## De tabel uit de README

| # | Stap | Input → output |
|---|---|---|
| 1 | Ingest | Upload → S3 + DB-record |
| 2 | Classificatie | Bestand → type (DXF / vector-PDF / raster / IFC) |
| 3 | Normalisatie | Pagina's als PNG + vectordata, schaal bepaald |
| 4a | Vector-extractie | DXF/IFC → blokken, lagen, coördinaten |
| 4b | Detectie (raster) | PNG → bounding boxes per symbool |
| 4c | Legenda en tekst | OCR + VLM |
| 5 | VLM-redenering | Ruimtes, onzekere detecties, legenda-koppeling |
| 6 | Fusie | Alle bronnen → één `Project` |
| 7 | Validatie | `Project` → waarschuwingen |
| 8 | Materiaalengine | Symbool → artikel → hoeveelheid → prijs |
| 9 | Output | Excel, PDF-offerte, DXF |
| 10 | Review en feedback | Correcties → trainingsdata |

Elke stap is een eigen Celery-task met getypte input en output. Zie [017-taken-architectuur](017-taken-architectuur.md).

## Waarom deze volgorde

De volgorde volgt één regel: **van grof naar fijn, van waarnemen naar besluiten.**

- Stappen 1–3 zijn **voorbereidend**: ze maken verschillende formaten vergelijkbaar.
- Stappen 4–5 zijn **waarnemend**: ze produceren losse observaties.
- Stap 6 is **synthetisch**: één representatie.
- Stappen 7–9 zijn **afleidend**: code, geen modellen.
- Stap 10 is **menselijk**: controle en leren.

Zie [014-systeemlagen](014-systeemlagen.md) voor de laaggedachte erachter.

## De vertakking bij stap 4

Stap 4 heeft drie varianten die parallel draaien, afhankelijk van het geclassificeerde type:

| Type | 4a vector | 4b detectie | 4c tekst |
|---|---|---|---|
| DXF | ✅ | ❌ (optioneel: ter controle) | ✅ |
| IFC | ✅ | ❌ | ✅ |
| Vector-PDF | ✅ | ❌ | ✅ |
| Raster (gescand/foto) | ❌ | ✅ | ✅ |

Zie [016-hybride-aanpak](016-hybride-aanpak.md).

## Waar de tijd heen gaat

Indicatief, voor een gemiddelde woningtekening:

| Stap | Verwachte duur | Dominante kostenpost |
|---|---|---|
| 1 ingest | < 1 s | netwerk |
| 2 classificatie | < 1 s | I/O |
| 3 normalisatie | 2–10 s | rendering, tegelen |
| 4a vector | 1–5 s | parsing |
| 4b detectie | 10–40 s | GPU |
| 4c tekst | 5–20 s | GPU (OCR) |
| 5 VLM | 10–60 s | GPU (tokens) |
| 6 fusie | < 1 s | CPU |
| 7 validatie | < 1 s | CPU |
| 8 materiaal | < 1 s | CPU |
| 9 output | 1–5 s | I/O |
| 10 review | menselijk | — |

**Inzicht:** het VLM is de bottleneck. Dat is precies de reden om het alleen in te zetten waar het moet ([016-hybride-aanpak](016-hybride-aanpak.md)) en om vectorbronnen zoveel mogelijk te benutten.

## Waar de pipeline moet kunnen falen

Elke stap moet:

- een **begrijpelijke foutmelding** produceren ("Dit PDF-bestand is beveiligd met een wachtwoord"),
- **idempotent** zijn (opnieuw draaien levert hetzelfde resultaat),
- een **timeout** hebben,
- tussentijds resultaat wegschrijven zodat hervatten bij de laatste stap kan.

Zie [090-foutscenario](090-foutscenario.md).

## Wat er nu bestaat

Niets van de pipeline is geïmplementeerd. De structuur staat: `apps/worker/README.md` (Celery tasks) en het schema dat elke stap als output heeft. Zie [030-schema-verschillen-met-readme](030-schema-verschillen-met-readme.md).
