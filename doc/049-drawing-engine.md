# 049 — De tekenengine

## De rol

[packages/drawing](../packages/drawing) maakt **echte** tekeningen: DXF-bestanden die in AutoCAD, BricsCAD of een viewer openen, met symbolen, kabelroutes en maatvoering.

Dit onderscheidt het project van "een AI die plaatjes genereert": een gegenereerd plaatje is niet meetbaar, niet bewerkbaar en niet uitwisselbaar. Een DXF wel.

## De bibliotheek: ezdxf

Dezelfde library als voor het uitlezen ([042-parsers-dxf](042-parsers-dxf.md)) — dat is bewust: één afhankelijkheid voor in- en uitvoer, en dezelfde begrippen.

## De functies

### 1. Blokken definiëren

```python
def definieer_symboolblokken(doc):
    for type_, tekening in SYMBOLDRAWINGS.items():
        block = doc.blocks.new(name=f"IMJAN-{type_.value.upper()}")
        tekening(block)   # tekent cirkel, vierkant, kruis, ...
```

De bloktekeningen zijn vastgelegd in een centrale tabel zodat alle tekeningen identieke symbolen gebruiken.

### 2. Symbolen plaatsen

```python
def plaats_symbool(doc, symbool: Symbol):
    block = doc.blocks.get(f"IMJAN-{symbool.type.value.upper()}")
    doc.modelspace().add_blockref(
        block.name,
        insert=(symbool.x, symbool.y),
        dxfattribs={"rotation": symbool.rotation},
    )
```

### 3. Kabels tekenen

```python
def teken_kabel(doc, punten: list[tuple[float, float]], laag: str = "E-KABEL"):
    doc.modelspace().add_lwpolyline(punten, dxfattribs={"layer": laag})
```

### 4. Maatvoering

```python
def voeg_maat_toe(doc, start, einde, offset):
    dim = doc.modelspace().add_linear_dim(
        base=(start[0], start[1] - offset),
        p1=start, p2=einde,
    )
    dim.render()
```

### 5. Exporteren

```python
def exporteer(doc, pad: str):
    doc.saveas(pad)
```

## Wat het MCP-kant verbindt

Deze functies zijn de implementatie achter de MCP-tools:

| MCP-tool | Functie |
|---|---|
| `create_drawing` | Nieuw document + lagen |
| `place_symbol` | `plaats_symbool` |
| `draw_cable` | `teken_kabel` |
| `add_dimension` | `voeg_maat_toe` |
| `export_dxf` | `exporteer` |

Zie [056-mcp-tools](056-mcp-tools.md).

## Ontwerpregel: elke tool geeft een `Project`-wijziging terug

De README stelt:

> in productie worden tekeningen opgeslagen in storage (niet in-memory) en geeft elke tool een `Project`-wijziging terug, zodat alles controleerbaar en terug te draaien is.

Dat betekent: elke teken-actie resulteert in een diff op `Project`, die geauditeerd en ongedaan gemaakt kan worden. Zie [055-mcp-server](055-mcp-server.md).

## Laagstructuur

Een DXF zonder lagen is onbruikbaar voor de ontvanger. Minimale set:

| Laag | Inhoud |
|---|---|
| `IMJAN-SYMBOLEN` | Geplaatste symbolen |
| `IMJAN-KABELS` | Kabelroutes |
| `IMJAN-MAAT` | Maatvoering |
| `IMJAN-TEKST` | Labels en notities |
| `A-WANDEN` | Bestaande bouwkundige achtergrond |

## Wat er nu bestaat

Niets. [packages/drawing](../packages/drawing) is leeg; `ezdxf` staat in [pyproject.toml](../pyproject.toml).
