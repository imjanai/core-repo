# 050 — Afhankelijkheidskaart

## Welk pakket hangt van wat af

```
schema          (pydantic)
   ▲   ▲   ▲   ▲   ▲
   │   │   │   │   └── rules        (verder niets)
   │   │   │   └────── materials    (verder niets)
   │   │   └────────── parsers      (ezdxf, pymupdf, pdfplumber, ifcopenshell)
   │   └────────────── drawing      (ezdxf)
   └────────────────── vision       (ultralytics, sahi, openai, transformers)
```

**Regel:** niets mag naar boven wijzen. `schema` importeert nooit uit een ander pakket.

## De apps

```
apps/api        → schema, materials, rules, drawing, sqlalchemy, fastapi
apps/worker     → schema, parsers, vision, rules, materials, drawing, celery
apps/mcp_server → schema, drawing, mcp
apps/web        → (geen Python; deelt alleen typen via OpenAPI)
apps/review     → schema, materials
```

## De ML-wereld

```
ml/             → schema, vision, torch, transformers, peft, mlflow
```

`ml` is bewust de zwaarste tak: hij hangt van `schema` en `vision` af, maar **niemand hangt van `ml` af**. Training gebeurt buiten de servedi. Zie [072-mlops-en-registratie](072-mlops-en-registratie.md).

## Cyclische importen voorkomen

Een cyclische import is bijna altijd een ontwerpfout. Signalen:

- `schema` heeft iets van `materials` nodig → verkeerd om; materiaallogica hoort in `materials`.
- `parsers` wil `Symbol` maken → dat kan: `Symbol` komt uit `schema`, en `schema` kent `parsers` niet.
- `rules` heeft `materials` nodig → overweeg beide boven `schema` te plaatsen en het resultaat samen te voegen in de worker.

Vuistregel: **afhankelijkheden wijzen altijd naar beneden, naar `schema`.**

## Zware dependencies begrenzen

| Package | Zwaar? | Wie mag het |
|---|---|---|
| `torch` | ja (~2 GB) | alleen `vision` en `ml` |
| `transformers` | ja | alleen `vision` en `ml` |
| `paddleocr` | ja | alleen `vision` |
| `ezdxf` | nee | `parsers`, `drawing` |
| `pymupdf` | middel | `parsers` |
| `weasyprint` | middel (systeemlibs) | alleen de output-laag |
| `pydantic` | nee | iedereen |

**Waarom dat telt:** als `apps/api` van alles afhangt, wordt elke container gigabytes en elke deploy traag. Door de scheiding kan de API-container licht zijn en draait de GPU-workload in een eigen worker.

## Wat er nu misgaat

[packages/rules/rules.py](../packages/rules/rules.py) importeert `from schema import Project` — een pakket dat niet bestaat. Dat is precies het soort fout dat een afhankelijkheidskaart voorkomt: de afhankelijkheid staat niet in een pakket-bestand maar in een losse import.

**Fix:** zie [026-schema-export](026-schema-export.md).

## Hoe je dit handhaaht

1. Per pakket een eigen `pyproject.toml` met expliciete `dependencies` (zie [013-monorepo-workspace](013-monorepo-workspace.md)).
2. Een import-linter (bv. `import-linter`) met de regel: `schema` importeert niets.
3. Mypy per pakket, zodat ontbrekende typen in grenzen vroeg zichtbaar zijn.

```bash
uv run lint-imports   # na installatie van import-linter
```
