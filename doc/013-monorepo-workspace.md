# 013 — Monorepo en uv-workspace

## Wat is een workspace?

De hele repo is één Python-project met één [pyproject.toml](../pyproject.toml) aan de top. Er zijn nog geen losse packages met hun eigen `pyproject.toml` — de bedoeling (volgens de README-structuur) is een **uv-workspace** waarin `apps/*` en `packages/*` elk een eigen pakket zijn dat elkaar via de workspace kan importeren.

## De huidige `pyproject.toml`

```toml
[project]
requires-python = ">=3.11"
dependencies = [
  # API en taken
  "fastapi", "uvicorn[standard]", "pydantic>=2", "sqlalchemy>=2", "alembic",
  "asyncpg", "celery[redis]", "boto3", "python-multipart",
  # Tekening-parsing
  "ezdxf", "pymupdf", "pdfplumber", "ifcopenshell", "opencv-python-headless",
  # Vision / ML
  "torch", "transformers", "peft", "accelerate", "ultralytics", "sahi",
  "paddleocr", "qwen-vl-utils", "openai",
  # MCP
  "mcp",
  # Output
  "openpyxl", "weasyprint", "jinja2",
  # Kwaliteit en observability
  "pytest", "ruff", "mypy", "sentry-sdk", "langfuse", "mlflow",
]
```

Twee dingen vallen op:

1. **Eén grote dependency-lijst.** Alles hangt aan alles. Dat is handig in Fase 0, maar betekent dat een API-container ook `torch` meeneemt. Zie "Wat er later moet veranderen".
2. **Er is nog geen `[tool.uv.workspace]`** en geen per-pakket-afhankelijkheden.

## Hoe imports nu werken

In [packages/rules/rules.py](../packages/rules/rules.py):

```python
from schema import Project
```

Terwijl het bestand `packages/schema/project.py` heet met daarin `class Project`. Dat werkt alleen als `schema` op het PYTHONPATH staat en `schema/__init__.py` `Project` exporteert — wat nog niet bestaat. Dit is een **openstaand punt** dat opgelost moet worden voordat de regelengine testbaar is. Opties:

- `from packages.schema import Project` (als `packages` een pakket is met `__init__.py`), of
- een workspace-pakket `imjan-schema` dat anderen `from imjan_schema import Project` laten doen.

Zie [026-schema-export](026-schema-export.md) en [050-afhankelijkheidskaart](050-afhankelijkheidskaart.md).

## Wat uv doet

```bash
uv sync        # installeert alles volgens pyproject.toml + lockfile
uv run ...     # voert uit in de workspace-omgeving
```

- `uv sync` is snel (rusterustgebaseerd) en reproduceerbaar als `uv.lock` gecommit wordt.
- `uv run pytest`, `uv run ruff check .`, `uv run mypy .` — altijd in dezelfde omgeving.

## Wat er later moet veranderen

Werk richting een **workspace met meerdere pakketten**:

```toml
[tool.uv.workspace]
members = ["packages/*", "apps/*"]
```

En per pakket een eigen `pyproject.toml` met gerichte dependencies:

| Pakket | dependencies |
|---|---|
| `schema` | alleen `pydantic` |
| `rules` | `schema` |
| `parsers` | `ezdxf`, `pymupdf`, `pdfplumber`, `ifcopenshell` |
| `vision` | `ultralytics`, `sahi`, `openai` |
| `materials` | `schema`, eventueel `openpyxl` |
| `drawing` | `ezdxf`, `schema` |
| `apps/api` | `fastapi`, `sqlalchemy`, packages |
| `apps/worker` | `celery`, packages |
| `ml` | `torch`, `transformers`, `peft` — nergens anders |

**Waarom:** zo blijft de API-container licht en kan ML-onderhoud de servedi niet breken. Ook maakt het cyclische importen zichtbaar.

## Regels

- Voeg nooit een dependency toe aan de top-lijst als alleen één package hem nodig heeft — werk toe naar per-pakket-afhankelijkheden.
- Commit `uv.lock`.
- Gebruik `uv run` in plaats van een geactiveerde venv, zodat iedereen dezelfde omgeving heeft.
