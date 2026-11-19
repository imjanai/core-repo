# 048 — De materiaalengine

## De opgave

Van `Project` naar een inkoopklare lijst:

```
symbool → artikel → hoeveelheid → stuksprijs → regelprijs
```

Dit is waar het platform direct geld bespaart: een fout hier is een verkeerde bestelling.

## De drie onderdelen

### 1. Catalogus

Een lijst artikelen:

```python
class Artikel(BaseModel):
    artikelnummer: str
    omschrijving: str
    etim_code: str | None
    stuksprijs: float
    eenheid: str = "st"
    leverancier: str | None = None
```

**Herkomst:** groothandel-feed, CSV, of een handmatig onderhouden bestand. ETIM-classificatie maakt koppeling met meerdere leveranciers mogelijk.

### 2. Mapping

```python
MAPPING = {
    SymbolType.WCD:    "WCD-86-RVS",
    SymbolType.SWITCH: "SCH-1V-W",
    SymbolType.LIGHT:  "LP-PLAF-W",
    SymbolType.DATA:   "NET-CAT6-K",
    SymbolType.PANEL:  "GK-12M-W",
}
```

De mapping is bewust eenvoudig: symbooltype → standaardartikel. Uitbreidingen:

- **varianten per ruimte** (badkamer: IP44-artikel),
- **varianten per land** (Belgisch versus Nederlands materiaal),
- **klant-specifieke voorkeuren** (per tenant).

### 3. Engine

```python
def materialiseer(p: Project) -> list[MaterialLine]:
    counts = Counter(s.type for s in p.symbols)
    return [
        MaterialLine(
            artikelnummer=MAPPING[t],
            omschrijving=ARTIKELEN[MAPPING[t]].omschrijving,
            aantal=n,
            stuksprijs=ARTIKELEN[MAPPING[t]].stuksprijs,
            regelprijs=n * ARTIKELEN[MAPPING[t]].stuksprijs,
        )
        for t, n in counts.items()
    ]
```

**Let op:** dit is deterministische code over `Project`. Geen model, geen interpretatie. Zie principe 3 in [006-ontwerpprincipes](006-ontwerpprincipes.md).

## Wat er nog bij komt

| Onderdeel | Waarom |
|---|---|
| **Materiaal per symbool** (niet alleen per type) | Een WCD op zich is niet compleet: doos, inbouwdoos, aftakdoos |
| **Verbruiksartikelen** | Kabel per meter, leiding, tie-wraps — afgeleid uit routes, niet uit symbolen |
| **Montage-units** | Groepenkast als set |
| **Afval en marge** | 5–10% overhead, per categorie |
| **Arbeid** | Minuten per symbooltype × tarief — voedt de offerte |

## De afhankelijkheid met de tekeningen

Een nauwkeurige materiaallijst vraagt om nauwkeurige symbolen. Daarom is de materiaalengine ook de **beste test van het hele systeem**: de fout in de uiteindelijke lijst (aantal en kosten) is een betere maatstaf dan mAP. Zie [069-metrics](069-metrics.md).

## Output

```python
class MaterialLine(BaseModel):
    artikelnummer: str
    omschrijving: str
    aantal: int
    stuksprijs: float
    regelprijs: float
    ruimte_id: str | None = None
    circuit: str | None = None
```

Export naar Excel via openpyxl, naar PDF via Jinja2 + WeasyPrint. Zie [040-stap-7-tot-10](040-stap-7-tot-10.md).

## Wat er nu bestaat

Niets. [packages/materials](../packages/materials) is leeg; `openpyxl`, `weasyprint` en `jinja2` staan in [pyproject.toml](../pyproject.toml).
