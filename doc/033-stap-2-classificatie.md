# 033 — Stap 2: Classificatie

## De vraag

> Wat voor bestand is dit écht, en welk analysepad moet draaien?

Bestandsnaam-extension is een aanwijzing, geen antwoord: `.pdf` kan vector of gescan zijn, `.dxf` kan corrupt of eigenaardig geëncod zijn.

## De vier categorieën

| Type | Herkenning | Pad |
|---|---|---|
| **DXF** | `%`-header of `SECTION`-blokken; ezdxf `readfile()` slaagt | vector |
| **IFC** | `ISO-10303-21` header; `ifcopenshell.open()` slaagt | vector |
| **Vector-PDF** | PDF met `stream`-objecten met `re`/`m`/`l`-operatoren, weinig `/Image` | vector (met extractie) |
| **Raster** | PDF met voornamelijk `/Image`, of PNG/JPEG direct | raster |

## De implementatie

```python
def classify(path: str) -> Literal["dxf", "ifc", "vector_pdf", "raster", "unknown"]:
    if _is_dxf(path):   return "dxf"
    if _is_ifc(path):   return "ifc"
    if _is_pdf(path):   return "vector_pdf" if _pdf_has_vectors(path) else "raster"
    if _is_image(path): return "raster"
    return "unknown"
```

`_pdf_has_vectors` telt bijvoorbeeld het aantal vectoroperatoren versus het aantal pixel-pagina's. Een simpele heuristiek werkt beter dan je denkt: gescande PDF's hebben per pagina één groot `/Image`-object en geen tekst.

## Waarom dit een eigen stap is

1. **De vertakking** — 4a en 4b zijn verschillende taken met verschillende hardware. De worker moet weten welke te starten.
2. **Kosten** — een rasterpad op een DXF kost GPU-tijd voor niets; een vectorpad op een scan levert niets op.
3. **Foutkwaliteit** — als classificatie verkeerd is, is de foutmelding later onbegrijpelijk ("geen symbolen gevonden" op een scan die als DXF werd behandeld).

## Randgevallen

| Randgeval | Aanpak |
|---|---|
| DWG (gesloten formaat) | Via ODA File Converter naar DXF, dan opnieuw classificeren |
| PDF met gemengde pagina's (tekst + scan) | Per pagina classificeren, niet per bestand |
| Vector-PDF uit Illustrator met afwijkende operator-volgorde | Val terug op: veel tekst + weinig image = vector |
| HEIC van iPhone | Converteren naar PNG vóór analyse |
| ZIP-map | Niet ondersteund in MVP |

## Output

Een eenvoudige enum die meereist door de rest van de pipeline:

```python
class BestandsType(str, Enum):
    DXF = "dxf"
    IFC = "ifc"
    VECTOR_PDF = "vector_pdf"
    RASTER = "raster"
```

## Wat er nu bestaat

Niets. Zie [031-pipeline-overview](031-pipeline-overview.md) voor de plaats in het geheel.
