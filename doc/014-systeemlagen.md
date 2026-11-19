# 014 — De systeemlagen

Het platform is opgebouwd in vijf lagen. Elke laag heeft één verantwoordelijkheid en praat alleen met de buren.

## Laag 1 — Ingest

**Taak:** bestanden aannemen, veiligstellen, vastleggen.

- Upload → S3-compatibele opslag
- DB-record met metadata (bestandstype, grootte, eigenaar, tenant)
- Auth-controle en quota

**Regel:** deze laag doet nog geen analyse. Houdt uploads snel en foutbestendig.

Meer: [032-stap-1-ingest](032-stap-1-ingest.md), [060-opslag-en-s3](060-opslag-en-s3.md).

## Laag 2 — Analyse (waarnemen)

**Taak:** waarnemingen produceren, niet besluiten.

Drie sporen, elk met hun eigen sterkte:

| Spoor | Input | Output |
|---|---|---|
| Vector-parser | DXF / IFC / vector-PDF | blokken, lagen, exacte coördinaten |
| Symbooldetector | PNG-tegels | bounding boxes + class + confidence |
| VLM | afbeelding + tekstvragen | interpretaties, legenda, ruimtes |

**Regel:** elke waarneming draagt een `confidence` en een `source` ([023-symbol-model](023-symbol-model.md)). De laag beslist niet wat "waar" is — dat doet de fusie.

Meer: [035](035-stap-4a-vector-extractie.md), [036](036-stap-4b-detectie.md), [037](037-stap-4c-tekst-en-legenda.md), [038](038-stap-5-vlm-redenering.md).

## Laag 3 — Model (samenvoegen)

**Taak:** één `Project` produceren.

De fusiestep kiest per object de beste bron, deelt ruimtes toe en erft conflicten als waarschuwingen. Vanaf hier is er **één representatie** van de werkelijkheid.

**Regel:** alles na deze laag werkt uitsluitend op `Project`. Geen enkele component mag nog naar een DXF of PNG grijpen.

Meer: [039-stap-6-fusie](039-stap-6-fusie.md), [021-schema-overview](021-schema-overview.md).

## Laag 4 — Afleiden (rekenen en regels)

**Taak:** nieuwe feiten afleiden uit het `Project` — deterministisch.

- **Materiaalengine:** symbool → artikel → hoeveelheid → prijs
- **Regelengine:** `Project` → waarschuwingen (NEN 1010)
- **Validatie:** formele controles

**Regel:** hier is géén taalmodel betrokken. Reproduceerbaar, testbaar, uitlegbaar. Zie principe 3 in [006-ontwerpprincipes](006-ontwerpprincipes.md).

Meer: [047](047-rules-nen-1010.md), [048](048-materials-engine.md).

## Laag 5 — Output en terugkoppeling

**Taak:** resultaten tonen en leren.

- Materiaallijst (Excel), offerte (PDF), tekening (DXF/PDF), rapport
- Review-UI waar de vakman corrigeert
- Correcties → trainingsdata → volgend model

**Regel:** de laatste schakel is een mens. Zie [085-aansprakelijkheid](085-aansprakelijkheid.md).

Meer: [040-stap-7-tot-10](040-stap-7-tot-10.md), [070-feedbackloop](070-feedbackloop.md).

---

## Waar de grenzen liggen

```
Ingest   →  "wat is er binnen?"        (geen interpretatie)
Analyse  →  "wat zie ik?"              (geen besluiten)
Model    →  "wat is het geheel?"       (geen berekeningen)
Afleiden →  "wat volgt eruit?"         (geen modelaannames)
Output   →  "wat zien mensen?"         (geen nieuwe analyse)
```

Als je merkt dat een laag werk van de buren doet — de parser die gaat rekenen, de VLM die gaat tellen, de materiaalengine die gaat gokken — is dat een ontwerpfout, geen detail.
