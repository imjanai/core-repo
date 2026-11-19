# 074 — Python en uv

## Python 3.11+

De README stelt 3.11+ als minimum. Waarom niet 3.9 of 3.12:

- **3.11** is significant sneller dan 3.10 (exception groups, betere tracebacks, snellere interpreter).
- **3.12** voegt taalfeatures toe die het schema aangenamer maken (`type`-aliases), maar ML-library-ondersteuning loopt soms achter op de nieuwste Python.
- De repo gebruikt al `str | None`-syntax (3.10+) in [packages/schema/symbol.py](../packages/schema/symbol.py).

In de praktijk: 3.11 is een veilige, brede basis.

## uv

```bash
uv sync       # installeer
uv run ...    # voer uit
```

**Wat uv is:** een snelle Python-packagemanager en -installer (in Rust geschreven, door Astral — de makers van ruff). Vervangt pip, pip-tools, virtualenv en (deels) poetry in één tool.

**Waarom:**

- **Snel.** `uv sync` in seconden in plaats van minuten.
- **Reproduceerbaar.** `uv.lock` legt exacte versies vast.
- **Workspace-ondersteuning.** Meerdere pakketten in één repo, precies wat [013-monorepo-workspace](013-monorepo-workspace.md) vraagt.
- **Eén tool minder** om te onderhouden.

## De huidige `pyproject.toml`

Een lange, gedeelde dependency-lijst. Prima voor Fase 0, maar:

- er is geen `[tool.uv.workspace]`,
- er is geen `[build-system]` (noodzakelijk voor workspace-pakketten),
- `uv.lock` is niet aanwezig in de repo (althans niet in de gevonden bestanden).

## Wat er moet gebeuren

1. `uv lock` draaien en `uv.lock` committen.
2. Workspace configureren met per-pakket-`pyproject.toml`'s.
3. Zware ML-dependencies isoleren in `ml` en `vision` — anders draagt elke container torch mee.

Zie [050-afhankelijkheidskaart](050-afhankelijkheidskaart.md).

## De toolchain

| Tool | Rol | Commando |
|---|---|---|
| **uv** | Omgeving en packages | `uv sync`, `uv run` |
| **ruff** | Linting + formatting | `uv run ruff check .`, `uv run ruff format .` |
| **mypy** | Statisch typen | `uv run mypy .` |
| **pytest** | Tests | `uv run pytest` |

Alle vier staan ze in de dependency-lijst. Zie [082-lint-types-format](082-lint-types-format.md) en [081-teststrategie](081-teststrategie.md).

## Een waarschuwing over de dependency-lijst

De lijst bevat packages die enorme downloads zijn (`torch`, `paddleocr`, `ifcopenshell`). Bij het opzetten van een lichte omgeving voor alleen de API is dat onhandig. De oplossing is de workspace-migratie: per pakket eigen dependencies, zodat `uv sync --package api` alleen het lichte deel ophaalt.

## Wat er nu bestaat

[pyproject.toml](../pyproject.toml) met `requires-python = ">=3.11"` en één dependency-groep. Geen lockfile gevonden.
