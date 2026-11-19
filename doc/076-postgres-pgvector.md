# 076 — PostgreSQL en pgvector

## De keuze

> **Database:** PostgreSQL + pgvector

## Waarom Postgres

1. **Row-level security** voor multi-tenant — zie [059](059-auth-en-multitenancy.md) en [086](086-multitenant-security.md).
2. **JSONB** — flexibele opslag voor het gedeeltelijke `Project` zonder een documentdatabase te hoeven.
3. **Relationale integriteit** — foreign keys op `project_id`, `symbol_id`, `room_id` voorkomen wees-correcties.
4. **Één systeem** — minder diensten, minder backup-verhalen, minder kosten.

Alternatieven vergeleken: [020-keuzes-en-alternatieven](020-keuzes-en-alternatieven.md).

## Waarom pgvector

pgvector voegt vectorzoekopdrachten toe aan Postgres. Mogelijke toepassingen in dit project:

| Toepassing | Voordeel |
|---|---|
| **Symbool-embeddings** | "Vind vergelijkbare symbolen op andere tekeningen" |
| **Deduplicatie** | Detecteren van dubbele uploads via perceptuele hashes |
| **Legenda-matching** | Onbekende bloknaam vergelijken met bekende namen |
| **Zoeken in tekeningen** | Semantisch zoeken over projecten |

**Eerlijk:** in de huidige vijf-klassen-pijplijn is pgvector nog niet nodig. Het staat klaar voor wanneer de materiaalcatalogus of het zoeken semantisch worden. Voeg het niet geforceerd toe.

## De opslagkeuze: JSONB of tabellen

### Optie A — JSONB per project

```sql
CREATE TABLE projecten (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  data jsonb NOT NULL,
  zoek vector GENERATED ALWAYS AS (embedding(data)) STORED
);
```

Plus: eenvoudig, directe mapping met het Pydantic-model.
Min: moeilijk te doorzoeken op individuele symbolen, indexeren is lastig.

### Optie B — ge-normaliseerde tabellen (aanbevolen)

Symbolen en ruimtes als eigen tabellen met indexen. Materiaal- en regelqueries worden dan gewone SQL met indexgebruik.

**Advies:** optie B, met JSONB voor wat overblijft (polygonen, tussenresultaten). Zie [075-fastapi-sqlalchemy-alembic](075-fastapi-sqlalchemy-alembic.md).

## Indexering

| Index | Waarop |
|---|---|
| B-tree | `projecten(tenant_id, created_at)` |
| B-tree | `symbolen(project_id)`, `symbolen(circuit)` |
| GIN | `ruimtes.polygon` (JSONB) |
| GIST | ruimtepolygonen voor spatial-queries (optie: PostGIS) |

### PostGIS?

Voor punt-in-polygoon en afstandsberekeningen is PostGIS de betere tool dan handmatige Python-code. Overweging: extra dependency, maar het verplaatst geometrie naar de database waar het snel is. Zie [024-room-model](024-room-model.md) voor de ontwerpvraag.

## Backups

`pg_dump` met schema + data, dagelijks, versleuteld, in een andere regio. Plus point-in-time recovery via WAL-archivering voor productie. Zie [090-foutscenario](090-foutscenario.md).

## Wat er nu bestaat

Niets. `asyncpg` staat in [pyproject.toml](../pyproject.toml); er is geen docker-compose of migratie.
