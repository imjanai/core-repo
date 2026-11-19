# 044 — PDF-parsing

## De uitdaging

PDF is het meest voorkomende formaat — en het lastigste. Eén bestandstype, twee totaal werelden:

- **vector-PDF**: geëxporteerd uit CAD; bevat lijnen, curves en tekst.
- **raster-PDF**: gescand of gefotografeerd; alleen pixels.

De classificatiestap (stap 2) scheidt ze. Zie [033-stap-2-classificatie](033-stap-2-classificatie.md).

## De twee libraries

### PyMuPDF (fitz)

Sterk in rendering en het uitlezen van de ruwe structuur:

```python
import pymupdf

doc = pymupdf.open("tekening.pdf")
page = doc[0]

# Als raster
pix = page.get_pixmap(dpi=300)

# Vector-informatie
paths = page.get_drawings()   # lijnen, rechthoeken, curves
```

`get_drawings()` is de sleutel voor vector-PDF: het levert de grafische operatoren, waarmee je vormen (cirkels die symbolen voorstellen) kunt detecteren.

### pdfplumber

Sterk in tekst en tabellen:

```python
import pdfplumber

with pdfplumber.open("tekening.pdf") as pdf:
    page = pdf.pages[0]
    words = page.extract_words()   # woord + bbox
    rects = page.rects
    lines = page.lines
```

De woordposities zijn cruciaal: een tekst "WCD" naast een cirkel suggereert een classificatie.

## Welke bibliotheek voor wat

| Taak | Library |
|---|---|
| Pagina naar PNG (300 DPI) | PyMuPDF |
| Vector-operatoren uitlezen | PyMuPDF (`get_drawings`) |
| Woordposities | pdfplumber |
| Tekstblokken en tabellen | pdfplumber |
| Zoeken naar "1:100" in de titelblok | pdfplumber |
| OCR toepassen op gescand | PaddleOCR op de PNG (stap 4c) |

## Herkenning van vector versus raster

Een simpele, betrouwbare heuristiek:

```python
def is_vector_pdf(doc) -> bool:
    for page in doc:
        images = page.get_images()
        drawings = page.get_drawings()
        if len(images) > 0 and len(images[0]) > 0:
            # één groot beeld per pagina = scan
            return False
    return True
```

Fijnere signalen: aanwezigheid van `/Font`-objecten, verhouding tekst-tegen-beeld, bestandsgrootte per pagina.

## Randgevallen

| Randgeval | Aanpak |
|---|---|
| **Beveiligd PDF** | Detecteer vroeg en meld "Dit PDF is beveiligd met een wachtwoord" |
| **Gemengde pagina's** (tekst + gescande bijlage) | Per pagina classificeren |
| **PDF met meerdere tekeningen op één pagina** | Detecteer kaders; optioneel per kader analyseren |
| **Geëxplodeerde vector-PDF** (uit Illustrator) | Patronen zijn rommeliger; val terug op de detector |
| **DXF-export-in-PDF met afwijkende operatorvolgorde** | Test tegen echte exports van AutoCAD, BricsCAD, Revit |

## Kwaliteit

De PDF-parser is de plek waar de meeste praktijkvarianten opduiken. Bouw dus een **corpus van echte tekeningen** (anonymized) en test er elke wijziging op. Dat corpus is ook de basis van de evaluatieset voor het vectorpad. Zie [068-evaluatieset](068-evaluatieset.md).

## Wat er nu bestaat

Niets. [packages/parsers](../packages/parsers) is leeg; `pymupdf` en `pdfplumber` staan in [pyproject.toml](../pyproject.toml).
