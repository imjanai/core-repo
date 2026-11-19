# 034 — Stap 3: Normalisatie

## Doel

Vanaf hier werkt de rest van de pipeline met **één intermediaire representatie**, ongeacht het bronformaat:

- rasterpagina's als PNG (voor detector, OCR, VLM),
- vectordata als JSON (voor de vector-parser),
- een bepaalde `scale` (mm per tekeningeenheid).

## Onderdelen

### 1. Converteren

| Bron | Actie |
|---|---|
| DXF | Openen met ezdxf; raster-renderen naar PNG voor visuele stappen; vector-extractie naar JSON |
| IFC | Openen met ifcopenshell; projecteren naar 2D-plattegrond; renderen |
| PDF | Pagina's als PNG met PyMuPDF; tekst en vector-operatoren apart extraheren |
| Afbeelding | Normaliseren van kleurruimte, oriëntatie (EXIF), formaat |

### 2. Tegelen (tiling)

Een A0-tekening op 300 DPI is ~14.000 × 9.900 pixels. Zo'n afbeelding door een detector duwen verkleint alles tot onherkenbaarheid.

Daarom: snijden in overlappende tegels, bv. 1024 × 1024 met 20% overlap, en per tegel detecteren. SAHI regelt dit. Zie [045-vision-detector](045-vision-detector.md).

**Waarom overlap:** een symbool op de naad wordt anders half gezien.

**Na detectie:** coördinaten terugprojecteren naar het originele beeld en overlappende boxes mergen (non-maximum suppression over tegels heen).

### 3. Schaal bepalen — het kritieke onderdeel

Zonder schaal zijn coördinaten betekeloos. De bronnen, in aflopende betrouwbaarheid:

| Bron | Betrouwbaarheid | Voorbeeld |
|---|---|---|
| DXF-header | ✅ exact | `$INSUNITS` = 4 (mm) |
| IFC | ✅ exact | projectielengte-eenheid |
| PDF vectordata | ⚠️ vaak afwezig | schaalaanduiding in titelblok |
| Tekstuele schaalaanduiding ("1:100") | ⚠️ goed, via OCR | meest voorkomend |
| Afstandsbekende maatvoering | 🔶 rekenkundig | meet een gemeten lijn, rekent de schaal terug |
| VLM-geschatte schaal | 🔶 als vangnet | laatste redmiddel |

De output is `Project.scale` — zie [022-project-model](022-project-model.md).

### Sanity-check

Zoals beschreven bij `scale`: controleer dat de bepaalde schaal plausibel is (typisch 0.1–1000 mm per eenheid). Een verkeerde eenheidskeuze (inch) levert 25.4 of 1/25.4 op. Log een waarschuwing als de waarde buiten de bandbreedte valt en leg de twijfel vast in `warnings` — niet stille corruptie.

## Wat er nog ontbreekt maar handig is

- **Ontdubbelen van pagina's** — sommige PDF's bevatten dezelfde tekening twee keer (tekening + index).
- **Zwart/wit-normalisatie** voor OCR (contrast).
- **Oriëntatie vastzetten** — een gedraaide scan levert een gedraaide tekening op; gebruik tekstdetectie om de juiste oriëntatie te kiezen.

## Output

```python
class NormalisatieOutput(BaseModel):
    project_id: str
    bestands_type: BestandsType
    pagina_png: list[str]        # S3-sleutels
    vectordata: str | None       # S3-sleutel
    scale: float
    scale_bron: str              # dxf_header | ocr | maatvoering | vlm | geschat
    waarschuwingen: list[str]
```

Het veld `scale_bron` is belangrijk: het laat in de review zien hoeveel vertrouwen de coördinaten verdienen, en het voedt de evaluatie ([069-metrics](069-metrics.md)).

## Wat er nu bestaat

Niets. Zie [031-pipeline-overview](031-pipeline-overview.md).
