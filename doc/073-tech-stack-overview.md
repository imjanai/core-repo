# 073 — Tech stack: alle keuzes per laag

## De tabel uit de README

| Laag | Keuze |
|---|---|
| **Basismodel** | Qwen-VL (fine-tuned; controleer licentie per modelgrootte) |
| **Fine-tuning** | PyTorch, Hugging Face Transformers + PEFT (LoRA/QLoRA), ms-swift of LLaMA-Factory |
| **Symboldetectie** | Ultralytics YOLO / RT-DETR, SAHI voor tiling |
| **OCR** | PaddleOCR (+ VLM voor lastige gevallen) |
| **Tekening-parsing** | ezdxf, PyMuPDF, pdfplumber, ifcopenshell, ODA File Converter |
| **Model-serving** | vLLM (OpenAI-compatibele API) |
| **Backend** | Python, FastAPI, SQLAlchemy, Alembic |
| **Taken** | Celery + Redis (later eventueel Temporal) |
| **Database** | PostgreSQL + pgvector |
| **Opslag** | S3-compatibel (MinIO / AWS S3, EU-regio) |
| **MCP** | Officiële MCP Python SDK |
| **Tekenengine** | ezdxf |
| **Frontend** | Next.js, React, TypeScript, Tailwind, shadcn/ui, PDF.js / OpenSeadragon + Konva |
| **Output** | openpyxl, WeasyPrint, Jinja2 |
| **MLOps** | MLflow of Weights & Biases, DVC |
| **Labeling** | CVAT, Label Studio |
| **Observability** | Sentry, Prometheus/Grafana, Langfuse |
| **Auth** | Keycloak of Auth0, row-level security in Postgres |
| **DevOps** | Docker, GitHub Actions, Terraform |
| **Tooling** | uv, ruff, mypy, pytest |

## De logica erachter

De stack volgt drie lijnen:

1. **Python zover het kan.** Parsing, ML, backend en taken in één taal: gedeelde types, één omgeving, één toolchain.
2. **Bewezen stukken, weinig eigen code.** FastAPI, Celery, Postgres, S3, vLLM — elk is de facto standaard in zijn niche. Minder eigen code betekent minder onderhoud.
3. **Zwaar gescheiden van licht.** GPU-werk (torch, vLLM) zit in packages en workers die het nodig hebben; de API blijft licht. Zie [050-afhankelijkheidskaart](050-afhankelijkheidskaart.md).

## Waar nog een keuze openstaat

| Onderwerp | Opties | Zie |
|---|---|---|
| IdP | Keycloak / Auth0 | [059](059-auth-en-multitenancy.md) |
| MLOps-platform | MLflow / W&B | [072](072-mlops-en-registratie.md) |
| Labeltool | CVAT / Label Studio | [067](067-labeling.md) |
| Detectiemodel | YOLO / RT-DETR | [065](065-symbooldetectie.md) |
| Taak-orchestratie | Celery / Temporal | [017](017-taken-architectuur.md) |

## Per laag dieper

| # | Document |
|---|---|
| 074 | [Python en uv](074-python-en-uv.md) |
| 075 | [FastAPI, SQLAlchemy, Alembic](075-fastapi-sqlalchemy-alembic.md) |
| 076 | [PostgreSQL en pgvector](076-postgres-pgvector.md) |
| 077 | [Redis en Celery](077-redis-en-celery.md) |
| 078 | [Frontend-stack](078-frontend-stack.md) |
| 079 | [Docker en infra](079-docker-infra.md) |
| 080 | [Observability](080-observability.md) |

## Wat er al vastligt in de repo

[pyproject.toml](../pyproject.toml) bevat de volledige dependency-lijst, inclusief de zware ML-library's. Er is nog geen workspace-configuratie en geen lockfile. Zie [013-monorepo-workspace](013-monorepo-workspace.md) en [030-schema-verschillen-met-readme](030-schema-verschillen-met-readme.md).
