# 020 — Keuzes en alternatieven

Elke belangrijke stackkeuze, het alternatief dat werd afgewezen, en waarom.

## Basismodel: Qwen-VL

| Optie | Pluspunt | Waarom niet |
|---|---|---|
| **Qwen-VL (gekozen)** | Sterk in visie-taal, meerdere groottes, actieve community | — |
| GPT-4o / Claude | Sterk | Gesloten API: geen fine-tuning, geen on-premise, dataverwerking bij derden |
| LLaVA | Open | Zwakker in fijne visuele details zoals symbolen |
| Pix2Struct | Open | Minder actief onderhoud |

**Aandachtspunt:** controleer de licentie per modelgrootte voor commercieel gebruik. Zie [062-basismodel-qwen-vl](062-basismodel-qwen-vl.md) en [087-modellicenties](087-modellicenties.md).

## Fine-tuning: LoRA/QLoRA

| Optie | Pluspunt | Waarom niet |
|---|---|---|
| **LoRA/QLoRA (gekozen)** | Goedkoop, weinig geheugen, snel itereren | — |
| Volledige fine-tune | Maximale aanpassing | Duur, risico op catastrophic forgetting |
| Few-shot, geen training | Geen data nodig | Geen garantie, duur per request |

**Gereedschap:** ms-swift of LLaMA-Factory — beide matuur; kiezen op onderhoud en Qwen-ondersteuning. Zie [063-finetuning-lora](063-finetuning-lora.md).

## Symboldetectie: YOLO / RT-DETR

| Optie | Pluspunt | Waarom niet |
|---|---|---|
| **YOLO (Ultralytics)** | Snel, makkelijk, veel voorbeelden | — |
| RT-DETR | Transformer, sterk bij overlap | Trager; wordt getest als alternatief |
| Detectron2 | Flexibel | Zwaarder in onderhoud |
| Alleen VLM | Eén model | Te traag en te duur voor detectie over duizenden symbolen |

SAHI erbij voor tiling: zonder verlies je kleine symbolen op grote tekeningen. Zie [045-vision-detector](045-vision-detector.md).

## Tekening-parsing

| Formaat | Library | Opmerking |
|---|---|---|
| DXF | **ezdxf** | De facto standaard; ook om te schrijven |
| PDF (vector) | **PyMuPDF** + **pdfplumber** | PyMuPDF voor rendering, pdfplumber voor tekst/tabellen |
| PDF (raster) | PaddleOCR | Voor gescande tekeningen |
| IFC | **ifcopenshell** | Volwaardige BIM-stack |
| DWG | **ODA File Converter** | DWG is gesloten; converter naar DXF als tussenstap |

Zie [042](042-parsers-dxf.md) t/m [044](044-parsers-pdf.md).

## Backend: FastAPI

| Optie | Pluspunt | Waarom niet |
|---|---|---|
| **FastAPI (gekozen)** | Async, Pydantic-native, OpenAPI gratis | — |
| Django | Admin, ORM ingebouwd | Zwaarder; SQLAlchemy is hier al de keuze |
| Flask | Licht | Geen typing, geen async, geen OpenAPI |

Merk op: [apps/api/README.md](../apps/api/README.md) zegt "FlaskAPI" — dat is een placeholder die niet klopt met de stackkeuze in de README en `pyproject.toml`. Zie [052-api-server](052-api-server.md).

## Taken: Celery + Redis

| Optie | Pluspunt | Waarom niet |
|---|---|---|
| **Celery (gekozen)** | Volwassen, veel documentatie | — |
| Temporal | Workflows als code | Overkill voor nu; bewaard als optie, zie [017](017-taken-architectuur.md) |
| RQ | Simpel | Minder controle over retries en queues |
| Arq / asyncio | Licht | Minder geschikt voor zware, lange taken |

## Database: PostgreSQL + pgvector

| Optie | Pluspunt | Waarom niet |
|---|---|---|
| **PostgreSQL (gekozen)** | RLS voor multi-tenant, JSONB, pgvector | — |
| MongoDB | Flexibel schema | Geen RLS, geen relationele integriteit |
| Separate vector-DB (Pinecone, Qdrant) | Snel | Extra dienst, extra kosten, data-splitting |

Eén database houdt multi-tenant eenvoudig en consistent. Zie [076-postgres-pgvector](076-postgres-pgvector.md).

## Model-serving: vLLM

| Optie | Pluspunt | Waarom niet |
|---|---|---|
| **vLLM (gekozen)** | Snel, OpenAI-compatibel, paging | — |
| Hugging Face TGI | Mature | vLLM doorgaans sneller voor LLM's |
| Triton | Veelzijdig | Meer configuratie voor hetzelfde |
| Eigen FastAPI-endpoint | Simpel | Traag en gevaarlijk op productie |

Zie [071-model-serving-vllm](071-model-serving-vllm.md).

## Opslag: S3-compatibel

MinIO lokaal (docker-compose), AWS S3 in EU-regio in productie. Dezelfde API, dus geen codeverschil. Zie [060-opslag-en-s3](060-opslag-en-s3.md).

## Frontend: Next.js + shadcn

Alternatieven afgewezen:

- **SvelteKit** — kleiner ecosysteem, minder herbruikbare componenten.
- **Traditionele React-SPA (Vite)** — zou werken; Next.js koos men voor SSR en routing-ecosysteem.
- **Zelf UI bouwen** — shadcn/ui levert toegankelijke, aanpasbare componenten zonder vendor-lock (de code staat in jouw repo).

Zie [078-frontend-stack](078-frontend-stack.md).

## Labeling: CVAT of Label Studio

Beide volwassen, open source. Label Studio integreert makkelijker met LLM-assisted labeling (handig bij grote volumes). Besluit valt bij de eerste labelronde op de evaluatieset. Zie [067-labeling](067-labeling.md).

## Observability: Sentry + Prometheus/Grafana + Langfuse

| Tool | Wat |
|---|---|
| Sentry | Fouten in code |
| Prometheus/Grafana | Systemen: latency, GPU, queue-lengte |
| Langfuse | Model-aanroepen: prompts, tokens, kosten, kwaliteit |

Zie [080-observability](080-observability.md).

## Auth: Keycloak of Auth0

| Optie | Pluspunt | Waarom niet |
|---|---|---|
| **Keycloak (self-hosted)** | Volledige controle, EU-hosting | Eigen onderhoud |
| Auth0 | SaaS, snel | Derde partij, kosten bij groei |
| Eigen implementatie | — | Nooit doen: veiligheidsrisico |

Besluit moet vallen vóór Fase 1 met pilotklanten. Zie [059-auth-en-multitenancy](059-auth-en-multitenancy.md) en [099-open-vragen](099-open-vragen.md).

## Tooling: uv, ruff, mypy, pytest

| Optie | Status |
|---|---|
| **uv** (i.p.v. pip/poetry) | Snel, moderne resolver, workspace-ondersteuning |
| **ruff** (i.p.v. flake8+isort+black) | Eén tool, veel sneller |
| **mypy** | Statisch typen — verplicht, niet optioneel |
| **pytest** | De facto standaard |

Zie [074-python-en-uv](074-python-en-uv.md) en [082-lint-types-format](082-lint-types-format.md).
