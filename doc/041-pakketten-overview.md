# 041 — De zes pakketten in `packages/`

## De verdeling

| Pakket | Taak | Status |
|---|---|---|
| `schema` | Pydantic-projectmodel, bron van waarheid | ✅ grotendeels |
| `parsers` | dxf, ifc, pdf uitlezen | 📋 leeg |
| `vision` | detector + VLM-client | 📋 leeg |
| `rules` | NEN 1010-regelengine | 🚧 eerste regel |
| `materials` | symbool → artikel → prijs | 📋 leeg |
| `drawing` | ezdxf tekenfuncties | 📋 leeg |

## Wat ze bindt

Alle zes werken op hetzelfde `Project`-model. Geen pakket definieert een eigen representatie van "een tekening". Zie [021-schema-overview](021-schema-overview.md).

```
parsers ─┐
vision  ─┼─►  fusie (worker) ─► Project ─► rules    ─► warnings
drawing ◄┘                                   ─► materials ─► prijzen
                                             ─► output    ─► bestanden
```

## Waarom losse pakketten en geen monoliet

1. **Testbaarheid.** `rules` is testbaar met een handgeschreven `Project` — geen GPU, geen S3, geen database. Dat is het verschil tussen een test die draait en een test die "later" geschreven wordt.
2. **Vervangbaarheid.** Een andere detector betekent alleen een nieuw `vision`-pakket; de rest merkt er niets van.
3. **Afhankelijkheden.** `rules` heeft geen `torch` nodig; `vision` wel. Aparte pakketten houden de installatie licht. Zie [050-afhankelijkheidskaart](050-afhankelijkheidskaart.md).
4. **Eigenaarschap.** Domeinlogica (`rules`, `materials`) wordt door een elektrotechnicus gereviewd; ML-code door een ML-ingenieur. aparte mappen maken die grens zichtbaar.

## Wat er per pakket moet komen

### `parsers`

- `dxf.py`: ezdxf-lezing → `list[VectorSymbol]`
- `ifc.py`: ifcopenshell → `list[VectorSymbol]` + `list[Room]`
- `pdf.py`: PyMuPDF + pdfplumber → vectordata + tekst
- `common.py`: gedeelde typen (`VectorSymbol`, `TextSpan`)

Zie [042](042-parsers-dxf.md), [043](043-parsers-ifc.md), [044](044-parsers-pdf.md).

### `vision`

- `detector.py`: YOLO/RT-DETR laden, per tegel voorspellen, NMS
- `tiling.py`: SAHI-wrappers
- `vlm_client.py`: aanroepen naar vLLM, JSON-output parsen en valideren
- `legend.py`: legenda-crops en -interpretatie

Zie [045](045-vision-detector.md), [046](046-vision-vlm-client.md).

### `rules`

- `rules.py`: `Rule`-dataclass, `RULES`-lijst, `validate()`
- per regel een bestand of een groep: belasting, beveiliging, badkamers, leidingen

Zie [047-rules-nen-1010](047-rules-nen-1010.md).

### `materials`

- `catalog.py`: artikelcatalogus (uit groothandel-feed of CSV)
- `mapping.py`: symbooltype → artikelnummer
- `engine.py`: `Project → list[MaterialLine]`

Zie [048-materials-engine](048-materials-engine.md).

### `drawing`

- `blocks.py`: symboolblokken definiëren
- `cables.py`: polylijnen voor kabelroutes
- `dimensions.py`: maatvoering
- `export.py`: DXF/PDF-export

Zie [049-drawing-engine](049-drawing-engine.md).

## Regels voor nieuwe code

- Geen netwerk in `packages/` — alleen pure logica over data. Netwerk hoort in `apps/`.
- Geen import uit `apps/` — andersom wel.
- Elke publieke functie getypt en met docstring.
- Elke functie een test met ten minste één randgeval.
