# 075 — FastAPI, SQLAlchemy en Alembic

## De trio

| Tool | Rol |
|---|---|
| **FastAPI** | HTTP-framework met validatie en OpenAPI |
| **SQLAlchemy 2.0** | ORM en query-laag, async |
| **Alembic** | Migraties voor de database-structuur |

Alle drie in [pyproject.toml](../pyproject.toml).

## FastAPI

```python
from fastapi import FastAPI, Depends

app = FastAPI(title="imjan AI")

@app.get("/projects/{project_id}")
async def haal_project(project_id: str, session=Depends(get_session)):
    return await session.get(ProjectRecord, project_id)
```

De twee dingen die FastAPI bijzonder maken voor dit project:

1. **Pydantic-native** — het `Project`-model uit [packages/schema](../packages/schema) is direct een response-model. Geen mapping-laag.
2. **OpenAPI** — `/docs` levert documentatie, en het schema voedt de frontend-typen. Zie [019-frontend-architectuur](019-frontend-architectuur.md).

## SQLAlchemy 2.0 (async)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase): pass

class ProjectRecord(Base):
    __tablename__ = "projecten"
    id: Mapped[str] = mapped_column(primary_key=True)
    tenant_id: Mapped[str]
    status: Mapped[str]
```

**Belangrijk in deze stack:**

- **Async.** De API is async; een sync-driver zou de event-loop blokkeren. Vandaar `asyncpg`.
- **RLS.** Zet `SET LOCAL app.tenant_id` in dezelfde transactie als de query. Zie [059-auth-en-multitenancy](059-auth-en-multitenancy.md).
- **JSONB voor het schema.** Een `Project` kan als JSONB worden opgeslagen (met GIN-index op symbolen), of ge-normaliseerd in tabellen `projecten`, `symbolen`, `ruimtes`. Beide werken; de keuze vraagt een ontwerpgesprek. Zie [099-open-vragen](099-open-vragen.md).

### Ge-normaliseerd (aanbevolen)

| Tabel | Kolommen |
|---|---|
| `projecten` | id, tenant_id, scale, status, created_at |
| `symbolen` | id, project_id, type, x, y, room_id, circuit, confidence, source |
| `ruimtes` | id, project_id, name, polygon (JSONB) |
| `warnings` | id, project_id, rule_id, severity, message |
| `correcties` | id, project_id, symbol_id, veld, oud, nieuw, reviewer |

Met indexen op `project_id`, `type` en `circuit` — precies wat de regelengine en de UI vragen.

## Alembic

```bash
uv run alembic init alembic
uv run alembic revision --autogenerate -m "init"
uv run alembic upgrade head
```

De README noemt deze stap bij het opstarten. Regels:

- **Elke schema-wijziging is een migratie**, geen handmatige DDL.
- **Autogenerate controleren** — het detecteert niet alles (bv. data-migraties).
- **Downgrades schrijven** waar het kan; dat maakt een mislukte deploy ongedaan.

## De relatie met het Pydantic-schema

Twee modellen, verschillende rollen:

| | Pydantic (`packages/schema`) | SQLAlchemy (`apps/api/models`) |
|---|---|---|
| Rol | Data-uitwisseling tussen onderdelen | Persistente opslag |
| Waar | Overal | Alleen de API/worker |
| Wijzigen | Brekend voor alle onderdelen | Binnen een migratie |

Converteer expliciet:

```python
def naar_pydantic(rec: ProjectRecord) -> Project:
    return Project(id=rec.id, scale=rec.scale, ...)
```

Nooit impliciet — de twee zullen op den duur divergeren.

## Wat er nu bestaat

Niets. `fastapi`, `sqlalchemy`, `alembic` en `asyncpg` staan in [pyproject.toml](../pyproject.toml).
