# 007 — Hoe werkt het? Het stroomschema

## Het overzicht

Dit is het diagram uit de README, met per blok een verwijzing naar het gedetailleerde document.

```
Upload (PDF / DWG / DXF / IFC / foto)
        │
        ▼
Preprocessing (converteren, tegelen, schaal bepalen, OCR)   → 034
        │
        ▼
Analyse-laag
  ├─ Vector parser (ezdxf / ifcopenshell)                   → 035
  ├─ Symbooldetector (YOLO / RT-DETR)                       → 036
  └─ Qwen-VL model (legenda, context, ruimtes, onzekere     → 037, 038
     gevallen)
        │
        ▼
Gestructureerd projectmodel (JSON / Pydantic)               → 021
        │
        ├─► Materiaalengine   (symbool → artikel → prijs)   → 048
        ├─► Validatie-engine  (NEN 1010 regels)             → 047
        └─► Agent-laag        (LLM + tools via MCP)         → 055
        │
        ▼
Output: materiaallijst, offerte, DXF/PDF-tekening, rapport  → 040
        │
        ▼
Review-UI → correcties → terug naar trainingsdata           → 070
```

## De vijf bewegingen

### 1. Ontvangen
Het bestand gaat naar S3 en er komt een database-record. Niets zwaars gebeurt nog — zo blijft de upload snel en foutbestendig. Zie [032-stap-1-ingest](032-stap-1-ingest.md).

### 2. Voorbereiden
Formaat bepalen, converteren naar gedeelde tussenstap (PNG-pagina's + vectordata), tegelen voor de detector en schaal bepalen. **Schaal is kritiek**: zonder schaal is `x` en `y` in `Symbol` geen mm maar een getal. Zie [034](034-stap-3-normalisatie.md).

### 3. Waarnemen (drie sporen parallel)
| Spoor | Sterk in | Zwak in |
|---|---|---|
| Vector-parser | DXF/IFC: exact, gratis, snel | Rasterbestanden |
| Symbooldetector | Herkent herhaalde objecten op afbeeldingen | Begrijpt geen legenda |
| Qwen-VL | Context, legenda, ruimtes, twijfelgevallen | Telt niet betrouwbaar |

Deze verdeling is principieel: zie [016-hybride-aanpak](016-hybride-aanpak.md).

### 4. Samenbrengen en afleiden
De fusiestap kiest per symbool de beste bron en markeert conflicterende waarnemingen met een `confidence` en `source` ([039](039-stap-6-fusie.md)). Daarna rekent code: regels, materiaal, prijzen.

### 5. Voorleggen en leren
De vakman beoordeelt in de review-UI. Correcties gaan terug als trainingsdata ([070](070-feedbackloop.md)).

## Waar de AI wél en niet aan te pas komt

| Onderdeel | Beslist de AI? |
|---|---|
| "Dit is een wandcontactdoos" | Ja (waarneming) |
| "Er staan er 12 op deze groep" | Nee — code telt |
| "Deze groep overschrijdt de belasting" | Nee — regelcode, grens uit de norm |
| "Dit lijkt een vergaderruimte" | Ja (interpretatie) |
| "Deze offerte klopt financieel" | Nee — berekening + menselijke goedkeuring |

## Terugkoppeling

Er is geen eindpunt: de review-stap voedt de trainingsset, die het volgende model voedt, dat de volgende analyse verbetert. Zie [070-feedbackloop](070-feedbackloop.md).
