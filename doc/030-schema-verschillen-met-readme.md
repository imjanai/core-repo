# 030 — Waar de code nu afwijkt van de README

Dit document verzamelt de **feitelijke** verschillen tussen wat de README beschrijft en wat er in de repo staat. Het is bewust nuchter: geen kritiek, maar een takenlijst.

## Overzicht

| Onderwerp | README zegt | Repo heeft | Impact |
|---|---|---|---|
| `apps/api` | FastAPI backend | README: "FlaskAPI Server" | Verwarrend; placeholder |
| `apps/review` | niet genoemd in de structuur | Map bestaat, README: "Security Reviewer" | Naamgeving onduidelijk |
| `apps/worker` | Celery tasks | Alleen README placeholder | Wacht op bouw |
| `apps/mcp_server` | MCP-tekentools | Map leeg | Wacht op bouw |
| `apps/web` | Next.js frontend | Map leeg | Wacht op bouw |
| `packages/parsers` | dxf, ifc, pdf | Map leeg | Wacht op bouw |
| `packages/vision` | detector + vlm-client | Map leeg | Wacht op bouw |
| `packages/materials` | symbool → artikel | Map leeg | Wacht op bouw |
| `packages/drawing` | ezdxf tekenfuncties | Map leeg | Wacht op bouw |
| `packages/rules` | NEN 1010 regelengine | 1 regel, brekende import 🚧 | Zie hieronder |
| `packages/schema` | Pydantic projectmodel | 4 bestanden ✅ maar geen export | Zie hieronder |
| `ml/data` | DVC-gebeheerd | Map leeg, geen `.dvc` | Wacht op data |
| `ml/train_detector.py` | detector-training | Leeg bestand | Wacht op invulling |
| `ml/finetune_vlm.py` | VLM fine-tuning | Leeg bestand | Wacht op invulling |
| `ml/eval` | evaluatieset + metrics | Map leeg | Wacht op set |
| `infra` | docker-compose, Terraform | Map leeg | Wacht op configuratie |
| `docs/` | genoemd in structuur | Bestaat niet (nu `doc/`) | Naamgevingsvraag |
| `pyproject.toml` | uv workspace | 1 dependency-lijst, geen workspace-config | Zie [013](013-monorepo-workspace.md) |
| Tests | `uv run pytest` | Geen enkele test | Wacht op eerste tests |

## De twee technische blokkades

### 1. De import in `packages/rules/rules.py` breekt

```python
from schema import Project
```

Dit importeert een `schema`-module die niet bestaat als pakket. Er is geen `schema/__init__.py`. Gevolg: elke `import packages.rules` faalt.

**Fix:** zie [026-schema-export](026-schema-export.md).

### 2. Er is geen export uit `packages/schema`

Zelfde probleem van de andere kant. `schema.py` bevat alleen een TODO.

## De naamgevingsvragen

### `doc/` versus `docs/`

De README-structuur noemt `docs/`. Deze map heet `doc/`. Kies één en houd vast.

### `apps/review` versus de review-UI

De README beschrijft een **review-UI** (elektricien corrigeert tekeningen). De map `apps/review` heet "Security Reviewer". Dat zijn twee verschillende dingen. De vermoedelijke bedoeling: `apps/review` wordt de review-UI, en de titel is een placeholder. Bevestig dat en pas de README aan.

### `apps/api` zegt Flask

Terwijl `pyproject.toml` FastAPI bevat en de README FastAPI noemt. Pas de placeholder aan.

## Wat ik zou doen, in volgorde

1. **Fix de import en de export** — klein werk, heft enorm (blokkeert alles in `packages/`).
2. **Schrijf één werkende test** die `from packages.rules import validate` draait en op een leeg `Project` niets teruggeeft. Dat sluit blokkade 1 af.
3. **Corrigeer de drie placeholders** (`apps/api/README.md`, `apps/review/README.md`, en de `doc`/`docs`-naam) zodat de repo zichzelf niet tegenspreekt.
4. **Kies één van beide**: ofwel je bouwt `infra/docker-compose.yml` vóór de eerste API-ontwikkeling, ofwel je start lokaal zonder Docker en documenteert dat.

## Hoe betrouwbaar is dit overzicht?

Het is gebaseerd op een glob van de hele repo op het moment van schrijven (12 bestanden). Als jij of een ander net iets toegevoegd heeft, klopt een regel niet meer. Voer bij twijfel opnieuw uit:

```bash
git ls-files
```
