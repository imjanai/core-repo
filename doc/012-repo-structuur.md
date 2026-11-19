# 012 — Repo-structuur

## De boom

```
elektro-ai/
├── apps/
│   ├── api/                 # FastAPI backend
│   ├── worker/              # Celery tasks (de pipeline)
│   ├── mcp_server/          # MCP-tekentools
│   └── web/                 # Next.js frontend
├── packages/
│   ├── schema/              # Pydantic projectmodel (bron van waarheid)
│   ├── parsers/             # dxf, ifc, pdf
│   ├── vision/              # detector + VLM-client
│   ├── rules/               # NEN 1010 regelengine
│   ├── materials/           # symbool → artikel → prijs
│   └── drawing/             # ezdxf tekenfuncties
├── ml/
│   ├── data/                # DVC-gebeheerd
│   ├── train_detector.py
│   ├── finetune_vlm.py
│   └── eval/                # evaluatieset + metrics
├── infra/                   # docker-compose, Terraform
├── docs/                    # (verwacht; zie notitie hieronder)
└── pyproject.toml           # uv workspace
```

## Wat er nu echt is

```
.
├── apps/
│   ├── api/README.md          # "FlaskAPI Server" (placeholder)
│   ├── review/README.md       # "Security Reviewer" (placeholder)
│   ├── worker/README.md       # "Celery tasks (de pipeline)"
│   ├── mcp_server/            # leeg
│   └── web/                   # leeg
├── packages/
│   ├── schema/                # project.py, symbol.py, room.py, schema.py ✅
│   ├── rules/rules.py         # eerste regel ✅
│   ├── parsers/               # leeg
│   ├── vision/                # leeg
│   ├── materials/             # leeg
│   └── drawing/               # leeg
├── ml/
│   ├── data/                  # leeg
│   ├── train_detector.py      # leeg
│   ├── finetune_vlm.py        # leeg
│   └── eval/                  # leeg
├── infra/                     # leeg
└── pyproject.toml             # dependencies ✅
```

## Waarom deze ordening

### `apps/` versus `packages/`

Dit is de belangrijkste scheiding in de repo:

- **`apps/`** = *delen die draaien*. Processen met een ingang: HTTP, queue, MCP-protocol, browser. Ze bevatten zo min mogelijk logica.
- **`packages/`** = *delen die redeneren*. Pure Python, geen server, geen netwerk. Ze nemen data in en geven data terug.

**Waarom:** packages zijn testbaar met een simpele `pytest`-aanroep, zonder database of GPU. Dat maakt de duurste fouten (domeinfouten) vroeg en goedkoop vindbaar.

### `ml/` apart

Training is een andere discipline dan servedi: andere dependencies (torch, CUDA), andere hardware, andere releasecyclus. Door `ml/` apart te houden kan de API licht blijven terwijl training zwaar is.

### `infra/` apart

Alles wat met deploy te maken heeft — docker-compose nu, Terraform later. Geen code, alleen configuratie.

## Openstaande punten

1. **README verwacht `docs/`, niet `doc/`.** De map in deze thread heet `doc/`; overweeg een rename of symlink zodat de twee niet uiteenvallen. Zie [099-open-vragen](099-open-vragen.md).
2. **`apps/review` staat niet in de README-structuur maar bestaat wel** als map. De README noemt de review-UI; de map heet `review`. Die naamgeving moet opgelost worden. Zie [057](057-review-app.md).
3. **`apps/api/README.md` zegt "FlaskAPI"**, terwijl de stack FastAPI is. Placeholder die gecorrigeerd moet worden.
4. **`packages/schema/schema.py`** is een TODO-placeholder voor het exporteren van subschema's. Zie [026](026-schema-export.md).

## Regels voor nieuwe mappen

- Nieuwe domeinlogica → `packages/<domein>/`
- Nieuw proces met een ingang → `apps/`
- Nieuwe pipeline-stap → `apps/worker` + tests in het bijbehorende package
- Nieuwe ML-experiment → `ml/`, nooit in `packages/`
- Configuratie → `infra/`
