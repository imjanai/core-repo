# 001 — Documentindex imjan AI

> Volledige AI-uitleg bij het project **imjan AI** — 100 documenten, opgebouwd vanuit de README, de repo-structuur en de huidige code.

Deze map (`doc/`) is de kennisbasis van het project. Elk bestand staat op zichzelf: je kunt een willekeurig document lezen zonder de rest te hebben gelezen. Begin bij `002-project-overview.md` als je het project niet kent, of gebruik dit bestand als navigatie.

## Legenda

| Symbool | Betekenis |
|---|---|
| ✅ | Geïmplementeerd in de huidige repo |
| 🚧 | Gedeeltelijk aanwezig |
| 📋 | Ontworpen/gepland, nog niet in code |

Sommige documenten beschrijven de **beoogde** situatie (zoals omschreven in de README) in plaats van de huidige code. Dat wordt per document vermeld.

---

## A. Overzicht en introductie (001–010)

| # | Bestand | Onderwerp |
|---|---|---|
| 001 | [001-index.md](001-index.md) | Dit bestand: navigatie over alle 100 documenten |
| 002 | [002-project-overview.md](002-project-overview.md) | Wat imjan AI is in één stuk |
| 003 | [003-probleemstelling.md](003-probleemstelling.md) | Welk probleem het platform oplost |
| 004 | [004-doelgroepen.md](004-doelgroepen.md) | Voor wie het gebouwd wordt |
| 005 | [005-waardepropositie.md](005-waardepropositie.md) | Waarom iemand zou betalen |
| 006 | [006-ontwerpprincipes.md](006-ontwerpprincipes.md) | De zes vaste uitgangspunten |
| 007 | [007-hoe-werkt-het.md](007-hoe-werkt-het.md) | Het stroomschema van upload tot output |
| 008 | [008-functieoverzicht.md](008-functieoverzicht.md) | Alle zeven functies en hun status |
| 009 | [009-status-en-roadmap.md](009-status-en-roadmap.md) | Fase 0 t/m 5, wat wanneer klaar is |
| 010 | [010-jargonwoordenboek.md](010-jargonwoordenboek.md) | Begrippenlijst voor niet-technici |

## B. Architectuur (011–020)

| # | Bestand | Onderwerp |
|---|---|---|
| 011 | [011-architectuur-overview.md](011-architectuur-overview.md) | Het grote plaatje van alle onderdelen |
| 012 | [012-repo-structuur.md](012-repo-structuur.md) | Mappen en waarom ze bestaan |
| 013 | [013-monorepo-workspace.md](013-monorepo-workspace.md) | uv-workspace en hoe pakketten samenkomen |
| 014 | [014-systeemlagen.md](014-systeemlagen.md) | Ingest, analyse, redenering, output, review |
| 015 | [015-dataflow-eind-tot-eind.md](015-dataflow-eind-tot-eind.md) | Pad van bestand tot materiaallijst |
| 016 | [016-hybride-aanpak.md](016-hybride-aanpak.md) | Waarom code én model, niet één van beide |
| 017 | [017-taken-architectuur.md](017-taken-architectuur.md) | Celery-taken en asynchrone verwerking |
| 018 | [018-api-grenzen.md](018-api-grenzen.md) | Welke diensten met elkaar praten |
| 019 | [019-frontend-architectuur.md](019-frontend-architectuur.md) | Opbouw van de Next.js-app |
| 020 | [020-keuzes-en-alternatieven.md](020-keuzes-en-alternatieven.md) | Waarom deze stack, wat waren de alternatieven |

## C. Projectmodel en schema (021–030)

| # | Bestand | Onderwerp |
|---|---|---|
| 021 | [021-schema-overview.md](021-schema-overview.md) | Het Pydantic-model als bron van waarheid |
| 022 | [022-project-model.md](022-project-model.md) | De `Project`-klasse in detail |
| 023 | [023-symbol-model.md](023-symbol-model.md) | De `Symbol`-klasse en alle velden |
| 024 | [024-room-model.md](024-room-model.md) | De `Room`-klasse en polygonen |
| 025 | [025-symboltype-enum.md](025-symboltype-enum.md) | De vijf symbooltypes en uitbreiding |
| 026 | [026-schema-export.md](026-schema-export.md) | `schema.py` en de openstaande TODO |
| 027 | [027-versiebeheer-van-het-schema.md](027-versiebeheer-van-het-schema.md) | Backward compatibility en migraties |
| 028 | [028-validatie-in-het-schema.md](028-validatie-in-het-schema.md) | Pydantic-validatie versus regelcontrole |
| 029 | [029-schema-uitbreiden.md](029-schema-uitbreiden.md) | Hoe voeg je een nieuw symbooltype toe |
| 030 | [030-schema-verschillen-met-readme.md](030-schema-verschillen-met-readme.md) | Waar code en README nu afwijken |

## D. De pipeline (031–040)

| # | Bestand | Onderwerp |
|---|---|---|
| 031 | [031-pipeline-overview.md](031-pipeline-overview.md) | De tien stappen op een rij |
| 032 | [032-stap-1-ingest.md](032-stap-1-ingest.md) | Upload naar S3 en database |
| 033 | [033-stap-2-classificatie.md](033-stap-2-classificatie.md) | DXF, vector-PDF, raster of IFC? |
| 034 | [034-stap-3-normalisatie.md](034-stap-3-normalisatie.md) | Tegelen, schaal bepalen, OCR-voorbereiding |
| 035 | [035-stap-4a-vector-extractie.md](035-stap-4a-vector-extractie.md) | Blokken, lagen en coördinaten uitlezen |
| 036 | [036-stap-4b-detectie.md](036-stap-4b-detectie.md) | Bounding boxes uit afbeeldingen |
| 037 | [037-stap-4c-tekst-en-legenda.md](037-stap-4c-tekst-en-legenda.md) | OCR en legenda-interpretatie |
| 038 | [038-stap-5-vlm-redenering.md](038-stap-5-vlm-redenering.md) | Ruimtes, twijfelgevallen, context |
| 039 | [039-stap-6-fusie.md](039-stap-6-fusie.md) | Alle bronnen samen tot één Project |
| 040 | [040-stap-7-tot-10.md](040-stap-7-tot-10.md) | Validatie, materiaal, output, review |

## E. Pakketten (041–050)

| # | Bestand | Onderwerp |
|---|---|---|
| 041 | [041-pakketten-overview.md](041-pakketten-overview.md) | De zes packages en hun taak |
| 042 | [042-parsers-dxf.md](042-parsers-dxf.md) | ezdxf en DXF-invoer |
| 043 | [043-parsers-ifc.md](043-parsers-ifc.md) | ifcopenshell en BIM-bestanden |
| 044 | [044-parsers-pdf.md](044-parsers-pdf.md) | PyMuPDF en pdfplumber |
| 045 | [045-vision-detector.md](045-vision-detector.md) | YOLO/RT-DETR en SAHI-tiling |
| 046 | [046-vision-vlm-client.md](046-vision-vlm-client.md) | Praten met het Qwen-VL-model |
| 047 | [047-rules-nen-1010.md](047-rules-nen-1010.md) | De regelengine, nu en straks |
| 048 | [048-materials-engine.md](048-materials-engine.md) | Symbool → artikel → prijs |
| 049 | [049-drawing-engine.md](049-drawing-engine.md) | Tekenen met ezdxf |
| 050 | [050-afhankelijkheidskaart.md](050-afhankelijkheidskaart.md) | Welk pakket hangt van wat af |

## F. Apps (051–060)

| # | Bestand | Onderwerp |
|---|---|---|
| 051 | [051-apps-overview.md](051-apps-overview.md) | De vijf apps in `apps/` |
| 052 | [052-api-server.md](052-api-server.md) | De FastAPI-backend |
| 053 | [053-api-endpoints.md](053-api-endpoints.md) | Alle routes en hun parameters |
| 054 | [054-worker-celery.md](054-worker-celery.md) | De Celery-worker en pipeline-taken |
| 055 | [055-mcp-server.md](055-mcp-server.md) | Waarom een MCP-server? |
| 056 | [056-mcp-tools.md](056-mcp-tools.md) | De vijf teken-tools in detail |
| 057 | [057-review-app.md](057-review-app.md) | De security-reviewer en de review-UI |
| 058 | [058-web-frontend.md](058-web-frontend.md) | Next.js, React, Tailwind, shadcn |
| 059 | [059-auth-en-multitenancy.md](059-auth-en-multitenancy.md) | Keycloak/Auth0 en row-level security |
| 060 | [060-opslag-en-s3.md](060-opslag-en-s3.md) | Bestandsopslag met MinIO of S3 |

## G. Machine learning (061–072)

| # | Bestand | Onderwerp |
|---|---|---|
| 061 | [061-ml-overview.md](061-ml-overview.md) | De volledige ML-kant in het kort |
| 062 | [062-basismodel-qwen-vl.md](062-basismodel-qwen-vl.md) | Qwen-VL kiezen en licenties |
| 063 | [063-finetuning-lora.md](063-finetuning-lora.md) | LoRA/QLoRA, ms-swift, LLaMA-Factory |
| 064 | [064-train-detector-script.md](064-train-detector-script.md) | Wat `ml/train_detector.py` moet doen |
| 065 | [065-symbooldetectie.md](065-symbooldetectie.md) | YOLO versus RT-DETR, mAP |
| 066 | [066-datasetstructuur.md](066-datasetstructuur.md) | DVC, COCO, JSONL, mappenindeling |
| 067 | [067-labeling.md](067-labeling.md) | CVAT en Label Studio |
| 068 | [068-evaluatieset.md](068-evaluatieset.md) | De heilige testset van ±50 tekeningen |
| 069 | [069-metrics.md](069-metrics.md) | Precisie, recall, materiaalfout |
| 070 | [070-feedbackloop.md](070-feedbackloop.md) | Correcties terug naar trainingsdata |
| 071 | [071-model-serving-vllm.md](071-model-serving-vllm.md) | vLLM en de OpenAI-compatibele API |
| 072 | [072-mlops-en-registratie.md](072-mlops-en-registratie.md) | MLflow/W&B, promoveren zonder regressie |

## H. Tech stack (073–080)

| # | Bestand | Onderwerp |
|---|---|---|
| 073 | [073-tech-stack-overview.md](073-tech-stack-overview.md) | Alle keuzes per laag |
| 074 | [074-python-en-uv.md](074-python-en-uv.md) | Python 3.11+, uv, `pyproject.toml` |
| 075 | [075-fastapi-sqlalchemy-alembic.md](075-fastapi-sqlalchemy-alembic.md) | Backend-framework en migraties |
| 076 | [076-postgres-pgvector.md](076-postgres-pgvector.md) | Databasekeuze en vectorzoekopdrachten |
| 077 | [077-redis-en-celery.md](077-redis-en-celery.md) | Queues, broker, resultaten |
| 078 | [078-frontend-stack.md](078-frontend-stack.md) | Next.js, TypeScript, Tailwind, shadcn, PDF.js |
| 079 | [079-docker-infra.md](079-docker-infra.md) | docker-compose en Terraform |
| 080 | [080-observability.md](080-observability.md) | Sentry, Prometheus, Grafana, Langfuse |

## I. Kwaliteit, veiligheid en compliance (081–090)

| # | Bestand | Onderwerp |
|---|---|---|
| 081 | [081-teststrategie.md](081-teststrategie.md) | pytest, unit, integratie, evaluatieset |
| 082 | [082-lint-types-format.md](082-lint-types-format.md) | ruff en mypy schoon houden |
| 083 | [083-cicd.md](083-cicd.md) | GitHub Actions en promotiegates |
| 084 | [084-veiligheid-en-avg.md](084-veiligheid-en-avg.md) | Hosting in de EU, bewaartermijnen |
| 085 | [085-aansprakelijkheid.md](085-aansprakelijkheid.md) | De vakman beslist, niet de AI |
| 086 | [086-multitenant-security.md](086-multitenant-security.md) | Row-level security en dat-isolatie |
| 087 | [087-modellicenties.md](087-modellicenties.md) | Qwen-licentie, commercieel gebruik |
| 088 | [088-secrets-en-configuratie.md](088-secrets-en-configuratie.md) | `.env`, nooit sleutels in git |
| 089 | [089-auditlogging.md](089-auditlogging.md) | Wie deed wat, en wanneer |
| 090 | [090-foutscenario.md](090-foutscenario.md) | Wat er misgaat en hoe we herstellen |

## J. Praktisch en ontwikkeling (091–100)

| # | Bestand | Onderwerp |
|---|---|---|
| 091 | [091-installatie.md](091-installatie.md) | Van clone tot draaiende stack |
| 092 | [092-omgevingsvariabelen.md](092-omgevingsvariabelen.md) | Alle `.env`-variabelen uitgelegd |
| 093 | [093-eerste-analyse.md](093-eerste-analyse.md) | Een DXF door de pipeline sturen |
| 094 | [094-conventional-commits.md](094-conventional-commits.md) | Commitberichten schrijven |
| 095 | [095-bijdragen.md](095-bijdragen.md) | Werken aan het project |
| 096 | [096-ontwikkelwerkruimte.md](096-ontwikkelwerkruimte.md) | Waar je aan wat bewerkt |
| 097 | [097-prestaties-en-schaal.md](097-prestaties-en-schaal.md) | Latency, doorvoer, GPU-budget |
| 098 | [098-kostenraming.md](098-kostenraming.md) | Wat het draaiend houden kost |
| 099 | [099-open-vragen.md](099-open-vragen.md) | Wat nog beslist moet worden |
| 100 | [100-productiechecklist.md](100-productiechecklist.md) | Alles wat af moet voor livegang |

---

## Leessuggesties

- **Nieuw in het team?** 002 → 007 → 011 → 012 → 031.
- **Backend-ontwikkelaar?** 021 → 031 → 052 → 054 → 075.
- **ML-ingenieur?** 061 → 062 → 063 → 066 → 068 → 071.
- **Frontend-ontwikkelaar?** 019 → 057 → 058 → 078.
- **Product of management?** 003 → 005 → 009 → 085 → 100.
