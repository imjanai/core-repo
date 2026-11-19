# 082 — Lint, types en formatting

## De tools

| Tool | Rol | Commando |
|---|---|---|
| **ruff** | Linting + formattering | `uv run ruff check .`, `uv run ruff format .` |
| **mypy** | Statisch typen | `uv run mypy .` |

Beide staan in [pyproject.toml](../pyproject.toml); de commando's staan in de README.

## Ruff

Ruff vervangt flake8, isort, pyupgrade en black in één tool — veel sneller.

Aanbevolen configuratie:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "RUF"]
```

| Groep | Wat |
|---|---|
| `E`, `F` | Syntax en fouten |
| `I` | Importvolgorde |
| `N` | Benaming (PEP8) |
| `UP` | Pyupgrade: moderne Python-syntax |
| `B` | Bugs (common mistakes) |
| `SIM` | Vereenvoudigingen |
| `RUF` | Eigen Ruff-checks |

## Mypy

Statisch typen is in dit project geen luxe: het `Project`-model is de drager van de hele architectuur, en mypy merkt op als iemand er een string in stopt in plaats van een enum.

```toml
[tool.mypy]
python_version = "3.11"
strict = true
plugins = ["pydantic.mypy"]
```

`strict = true` is ambitieus; een instap is `disallow_untyped_defs = true` — elke functie moet getypt zijn, zonder dat alles perfect hoeft te zijn.

### Waar mypy het meeste oplevert

- de grenzen tussen packages (input/output van elke stap),
- de regelengine (`Callable[[Project], list[str]]`),
- de API-handlers.

### Waar mypy het meest gezeurd wordt

- SQLAlchemy-modellen (vaak configuratie-overhead),
- externe libraries zonder stubs (`ifcopenshell`, `paddleocr`).

Los op met gerichte `# type: ignore` en `[[tool.mypy.overrides]]` per module — nooit globaal uitzetten.

## Het nut in dit project

De hele pipeline is een keten van getypeerde stappen. Met types krijg je:

- bij een wijziging van `Symbol` direct alle plekken die het raken,
- compiler-vingers op een verkeerde `source`-waarde,
- documentatie die klopt.

Dat is precies wat [006-ontwerpprincipes](006-ontwerpprincipes.md) principe 2 vraagt.

## Formattering

`uv run ruff format .` — altijd, overal, zonder discussie. Stel in als pre-commit hook:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.0
    hooks:
      - id: ruff
      - id: ruff-format
```

## Wat er nu bestaat

De tools staan in de dependencies; er is geen configuratie en geen hook.
