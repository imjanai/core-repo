# 091 — Installatie: van clone tot draaiende stack

## Vereisten

Uit de README:

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker en Docker Compose
- Node.js 20+ en pnpm (frontend)
- NVIDIA GPU met CUDA — **alleen** voor model-serving en training; **niet** nodig voor de DXF-flow

Die laatste nuance is belangrijk: zonder GPU kun je al parseren, rekenen en testen.

## De stappen

```bash
# 1. Clone
git clone https://github.com/imjanai/janai.git
cd janai

# 2. Python-omgeving
uv sync

# 3. Omgevingsvariabelen
cp .env.example .env
# vul database, S3 en vLLM-gegevens in

# 4. Services
docker compose -f infra/docker-compose.yml up -d

# 5. Database migreren
uv run alembic upgrade head

# 6. Frontend
cd apps/web && pnpm install && pnpm dev
```

De API draait op `http://localhost:8080` (docs op `/docs`); de frontend op `http://localhost:3000`.

## Wat er nu nog niet werkt

De meeste stappen verwachten bestanden die nog niet bestaan:

| Stap | Blokkade |
|---|---|
| `uv sync` | Werkt; haalt alle dependencies op (traag: torch etc.) |
| `cp .env.example .env` | `.env.example` bestaat niet |
| `docker compose up` | `infra/docker-compose.yml` bestaat niet |
| `alembic upgrade head` | Geen Alembic-configuratie |
| `pnpm dev` in `apps/web` | `apps/web` bestaat niet |
| `uvicorn apps.api.main:app` | `apps/api/main.py` bestaat niet |

Zie [030-schema-verschillen-met-readme](030-schema-verschillen-met-readme.md) voor de volledige inventaris.

## De minimale omgeving om wél te kunnen werken

Tot de stack er is, is dit genoeg voor schema- en regelwerk:

```bash
uv sync
uv run python -c "from packages.schema.project import Project; print(Project(id='t', scale=1.0))"
```

En na het oplossen van de import-fout in `rules`:

```bash
uv run pytest packages/
```

Zie [026-schema-export](026-schema-export.md).

## Zonder GPU

Draai alleen: postgres, redis, minio, api, worker (default-queue). Laat `vllm` weg en zet in de worker de stappen die GPU vragen op "overslaan". Documenteer dat als een officiële modus — het maakt ontwikkelen toegankelijk voor wie geen GPU heeft.
