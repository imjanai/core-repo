# 022 — Het `Project`-model

## De code

```python
# packages/schema/project.py
from pydantic import BaseModel, Field
from enum import Enum
from packages.schema.room import Room
from packages.schema.symbol import Symbol


class Project(BaseModel):
    id: str
    scale: float = Field(..., description="mm per tekeningeenheid")
    rooms: list[Room] = []
    symbols: list[Symbol] = []
    warnings: list[str] = []
```

## Veld per veld

### `id: str`

Identificator van het project. In de praktijk een UUID dat bij ingest wordt gegenereerd en in de database, S3-pad en alle Celery-taken meereist.

**Let op:** er is nu nog geen `tenant_id`; die is nodig voor multi-tenancy (row-level security). Zie [086-multitenant-security](086-multitenant-security.md).

### `scale: float` — "mm per tekeningeenheid"

Het belangrijkste veld voor correctheid. Een tekening heeft interne eenheden; `scale` zegt hoeveel millimeter er per eenheid overeenkomt.

| Situatie | `scale` |
|---|---|
| DXF in millimeters | `1.0` |
| DXF met eenheden op 1:100 ingesteld | `100.0` |
| Afbeelding zonder metadata, schaal uit legenda bepaald | geschatte waarheidsgetrouwe waarde |

**Waarom dit kritisch is:** `Symbol.x` en `Symbol.y` worden in mm opgeslagen. Zonder correcte `scale` zijn materiaallengtes (kabel, leiding) en maatvoering onjuist — en dat is precies de fout die direct geld kost.

**Risico:** `scale` is met `...` verplicht maar niet gevalideerd op plausibiliteit. Een DXF met een verkeerde eenheid (inch in plaats van mm) levert een scale van 25.4 of 1/25.4 op die er ongemerkt doorheen glijdt. Aanbeveling: een sanity-check in de normalisatiestap (verwacht range 0.1–1000). Zie [034-stap-3-normalisatie](034-stap-3-normalisatie.md).

### `rooms: list[Room]`

Ruimtes met polygoon. gevuld door de VLM of door vector-informatie (wanden uit DXF). Zie [024-room-model](024-room-model.md).

### `symbols: list[Symbol]`

De kern: alle herkende installatiepunten. Zie [023-symbol-model](023-symbol-model.md).

### `warnings: list[str]`

Berichten uit validatie en fusie. Nu platte strings.

**Ontwerpvraag:** strings zijn makkelijk maar niet structureerbaar. De review-UI wil een waarschuwing kunnen koppelen aan een specifiek symbool. Overweeg:

```python
class Warning(BaseModel):
    code: str          # bv. "grp-wcd"
    message: str
    symbol_ids: list[str] = []
    severity: str = "info"   # info | warn | error
```

Dat is een backward-incompatible wijziging — zie [027-versiebeheer-van-het-schema](027-versiebeheer-van-het-schema.md). Nu nog niet doen; wel vastleggen als plan.

## Wat er nog ontbreekt op `Project`

| Veld | Waarom nodig |
|---|---|
| `tenant_id` | Multi-tenant isolatie |
| `source_file` / `pages` | Herleidbaarheid naar het bronbestand |
| `created_at` / `updated_at` | Audit, caching, debugging |
| `schema_version` | Veilige migraties van opgeslagen projecten |
| `status` | Waar in de pipeline het project zich bevindt |
| `legend` | De symbool→type-koppeling die de legenda opleverde |

Deze horen in de API/DB-layer of in een uitgebreidere `Project`-variant; de keuze moet gemaakt worden vóór Fase 1. Zie [099-open-vragen](099-open-vragen.md).
