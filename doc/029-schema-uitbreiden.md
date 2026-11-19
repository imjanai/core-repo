# 029 — Het schema uitbreiden: hoe en wanneer

## Het uitgangspunt

Het schema is het contract waarin alle onderdelen spreken ([006-principe 2](006-ontwerpprincipes.md)). Elke wijziging raakt: parser, detector, fusie, regels, materialen, tekenengine, API, frontend, opgeslagen data en trainingsdata.

Dus: **voorzichtig, maar niet bang.**

## Stappenplan: een veld toevoegen

Neem als voorbeeld `rotation` op `Symbol` (nodig om via MCP te kunnen tekenen, zie [056-mcp-tools](056-mcp-tools.md)).

### 1. Voeg toe met default

```python
rotation: float = Field(default=0.0, description="graden, tegen de klok in")
```

Default betekent: bestaande data blijft geldig, en code die het veld niet kent, leest nog steeds een `Project`.

### 2. Vul het vanuit elke bron die het kan weten

- vector-parser: DXF-rotatie van het blok
- detector: afleiden uit de bounding box (lastig — vaak `0.0` tot de VLM het raadt)
- VLM: vragen bij twijfelgevallen
- human: review-UI

### 3. Voeg een test toe per bron

```python
def test_vector_levert_rotatie():
    project = parse_dxf(TEST_DXF)
    assert project.symbols[0].rotation == 90.0
```

### 4. Documenteer in de changelog van het schema

Zodat integratiepartners het weten.

### 5. Controleer serialization round-trip

```python
p2 = Project.model_validate(p1.model_dump())
assert p1 == p2
```

Zonder deze test is een wijziging in `model_config` of een alias onopgemerkt brekend.

## Stappenplan: een type toevoegen

Zie [025-symboltype-enum](025-symboltype-enum.md) — daar staat het volledige stappenplan inclusief hertraining van de detector.

## Wanneer je een wijziging níet moet doen

- **Tussen twee modelreleases in.** Elke veldwijziging betekent dat de trainingsdata en het schema weer moeten kloppen.
- **Voor één pilotklant.** Doe het generiek of niet.
- **Als een default verbergt wat er speelt.** Een default van `0.0` voor `confidence` is gevaarlijker dan geen default: het ziet er geldig uit terwijl het niets zegt.

## De koppeling met trainingsdata

Elk veld dat uit een model komt (`rotation`, `type`, `room_id`) heeft een labeltegenhanger in de dataset. Voeg je een veld toe zonder labelwerk, dan kan het model het nooit leren. Bespreek dus vóór schema-uitbreiding:

1. kunnen we dit labelen? ([067-labeling](067-labeling.md))
2. kunnen we het meten? ([069-metrics](069-metrics.md))
3. levert het op wat de MVP nodig heeft?

## Checklist vóór merged

- [ ] Default aanwezig of expliciet afgebroken (major bump)
- [ ] `model_dump()` / `model_validate()` round-trip test
- [ ] Export bijgewerkt in `__init__.py` (zie [026](026-schema-export.md))
- [ ] Import-wijziging doorgevoerd in `rules`, `materials`, `drawing`
- [ ] Frontend-typen gegenereerd
- [ ] Changelog bijgewerkt
