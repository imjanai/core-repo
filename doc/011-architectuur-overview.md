# 011 — Architectuur-overview

## Het plaatje

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (apps/web)                      │
│        Next.js · React · TypeScript · Tailwind · shadcn         │
│        PDF.js / OpenSeadragon (tekening) · Konva (overlays)     │
└──────────────┬──────────────────────────────────┬───────────────┘
               │ REST / JSON                      │ upload / review
┌──────────────▼──────────────────────────────────▼───────────────┐
│                     API (apps/api — FastAPI)                    │
│        Auth (Keycloak/Auth0) · row-level security               │
└──────┬─────────────────────────────────────────────┬────────────┘
       │ start taak                                  │ leest Project
┌──────▼──────────────────────────┐        ┌─────────▼────────────┐
│   WORKER (apps/worker — Celery) │        │  PostgreSQL + pgvector│
│   10 pipeline-stappen          │◄──────►│  projecten, symbolen  │
└──┬───────────┬───────────┬──────┘        └──────────────────────┘
   │           │           │
   │           │           └──────────────┐
┌──▼────────┐ ┌▼────────────┐ ┌───────────▼──────────────────────┐
│ PACKAGES  │ │ PACKAGES    │ │  MODEL SERVING (vLLM)            │
│ parsers   │ │ vision      │ │  Qwen-VL, OpenAI-compatibel API │
│ rules     │ │ (detector + │ └──────────────────────────────────┘
│ materials │ │  vlm-client)│
│ drawing   │ └─────────────┘
└───────────┘
       ▲
       │ alle packages lezen/wrijven hetzelfde schema
┌──────┴──────────────────────────────────────────────────────────┐
│              PACKAGES/schema  —  bron van waarheid              │
│        Project · Room · Symbol · SymbolType (Pydantic)          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  OPSLAG: S3-compatibel (MinIO lokaal, AWS S3 EU in productie)   │
│  MEDIUM: Redis (Celery-broker + cache)                          │
│  TEKENEN: apps/mcp_server (MCP-tools voor de agent)             │
│  ML: ml/ (training, fine-tuning, evaluatie)                     │
└─────────────────────────────────────────────────────────────────┘
```

## De rollen, in één alinea

De **frontend** laat de gebruiker uploaden en corrigeren. De **API** is de enige ingang, handhaaft auth en zet taken klaar. De **worker** voert de pipeline uit als losse, getypeerde taken. De **packages** bevatten alle domeinlogica — bewust los van de apps zodat ze testbaar zijn zonder server. Het **schema** is het contract waarin alles spreekt. **vLLM** serveert het model. **S3** bewaart bestanden, **Redis** taken.

## Waar die keuzes voor staan

| Keuze | Reden |
|---|---|
| Packages apart van apps | Domeinlogica testbaar zonder netwerk; herbruikbaar in worker én API |
| Schema als apart pakket | Eén bron van waarheid ([006-principe 2](006-ontwerpprincipes.md)) |
| Celery i.p.v. direct in de API | Analyse duurt seconden tot minuten; HTTP mag niet blokkeren |
| vLLM i.p.v. eigen serving-code | OpenAI-compatibel, snel, bewezen |
| pgvector in Postgres | Vectorzoekopdrachten bij de rest van de data, één databeheer |
| MinIO lokaal | Zelfde S3-API als productie, geen cloudafhankelijkheid tijdens ontwikkeling |

## Wat bewust níet in de diagram staat

- **Monitoring** (Sentry, Prometheus/Grafana, Langfuse) — doorsneden, zie [080](080-observability.md).
- **ML-training** — aparte wereld; die draait niet in de request-flow, zie [072](072-mlops-en-registratie.md).
- **Terraform** — alleen voor productie-infra, zie [079](079-docker-infra.md).

## Communicatiepatronen

| Van → Naar | Mechanisme |
|---|---|
| Frontend → API | HTTPS, JSON (REST) |
| API → Worker | Celery-message via Redis |
| Worker → packages | Directe function calls |
| Worker → model | HTTP, OpenAI-compatibel |
| Worker → storage | S3-protocol |
| Agent → tekenen | MCP (stdio/HTTP) |
| Alle → DB | SQLAlchemy (async) |

## Huidige status

Alleen `schema` en `rules` zijn in code aanwezig. De rest is ontwerp. Zie [002-project-overview#huidige-status](002-project-overview.md#huidige-status-van-de-repo) voor de eerlijke stand van zaken.
