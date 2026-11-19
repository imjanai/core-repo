# 056 — De vijf MCP-tools in detail

Elke tool: input, gedrag, teruggegeven wijziging, valkuilen.

## 1. `create_drawing`

**Input:**

```json
{"naam": "Woning Jansen — begane grond", "schaal": 100.0, "eenheid": "mm"}
```

**Gedrag:** maakt een nieuw document aan met de standaardlager ([049-drawing-engine](049-drawing-engine.md)) en een bijbehorend `Project`-record.

**Geeft terug:** `{project_id, versie: 0}`.

**Valkuilen:** schaal vergeten → later onbruikbare coördinaten. Maak `schaal` verplicht.

---

## 2. `place_symbol`

**Input:**

```json
{"type": "wandcontactdoos", "x": 12450.0, "y": 8300.0, "rotatie": 0.0, "ruimte_id": "r1"}
```

**Gedrag:** voegt een blokreferentie toe aan de DXF en een `Symbol` toe aan `Project`.

**Geeft terug:** de nieuwe `Symbol` (met `id`).

**Valkuilen:**

- **Coördinaten in mm versus tekeningseenheden.** De tool moet expliciet zijn over welke eenheid hij verwacht. Kies mm en reken intern om met `Project.scale`.
- **Onbekend type.** Valideer tegen `SymbolType`; een onbekend type is een fout, geen suggestie.
- **Buiten de tekening.** Waarschuw als de coördinaat buiten de tekenpunten valt — een klassieke hallucinatie van de agent.

---

## 3. `draw_cable`

**Input:**

```json
{"punten": [[12450, 8300], [12450, 9100], [14200, 9100]],
 "groep": "G3", "laag": "E-KABEL"}
```

**Gedrag:** tekent een lwpolyline en koppelt de route aan een groep.

**Geeft terug:** de route-id en de geplande lengte.

**Valkuilen:**

- **Lengteberekening** hoort bij code, niet bij de agent: meet de polygoon, niet wat de agent zegt.
- **Routes die dwars door muren lopen.** Optionele kruisingstest tegen wandlagen; waarschuw, blokkeer niet (de vakman beslist).

---

## 4. `add_dimension`

**Input:**

```json
{"van": [12450, 8300], "naar": [14200, 8300], "type": "lineair", "label": ""}
```

**Gedrag:** voegt maatvoering toe (`add_linear_dim` + `render()`).

**Geeft terug:** de maat en de berekende afstand.

**Valkuilen:** te veel maatvoering maakt een tekening onleesbaar. Stel een maximum in en/of laat de tool waarschuwen bij meer dan N maten.

---

## 5. `export_dxf`

**Input:**

```json
{"project_id": "…", "bestandsnaam": "tekening.dxf"}
```

**Gedrag:** slaat het document op in storage en geeft een presigned download-URL terug.

**Geeft terug:** `{url, verlopen_over: 3600, grootte_bytes}`.

**Valkuilen:**

- Exporteren zonder tussenopslag: als de agent vóór export crasht, is alles weg. **Sla periodiek op.**
- De URL mag niet publiek blijven. Kort leven, per object.

---

## Gemeenschappelijke regels

1. **Elke tool valideert zijn argumenten** — types, bereiken, Enum-waarden.
2. **Elke tool geeft een `Project`-diff terug** — controleerbaar en terug te draaien.
3. **Elke tool is idempotent waar mogelijk** — dubbele aanroep van `place_symbol` met dezelfde argumenten mag geen tweede symbool plaatsen (gebruik een client-idempotency-key).
4. **Elke tool logt** — wie, wat, wanneer. Zie [089-auditlogging](089-auditlogging.md).
5. **Elke tool faalt begrijpelijk** — "x moet binnen 0 en 100000 mm liggen" in plaats van een stacktrace.

## Het teruggegeven formaat

Eén schema voor alle tools:

```python
class ToolResult(BaseModel):
    ok: bool
    fout: str | None = None
    wijziging: ProjectDiff | None = None
    versie: int
```

`versie` is een oplopende teller per tekening — daarmee kun je conflict detecteren als twee agents tegelijk werken (optimistic concurrency).
