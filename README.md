# ⚡ imjan AI

> AI-platform voor elektriciens en installateurs: tekeningen analyseren, materiaallijsten genereren en installatietekeningen maken via MCP.

![status](https://img.shields.io/badge/status-in%20ontwikkeling-orange)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-propriëtair-lightgrey)

---

## Inhoudsopgave

1. [Introductie](#introductie)
2. [Wat kan het?](#wat-kan-het)
3. [Hoe werkt het?](#hoe-werkt-het)
4. [Tech stack](#tech-stack)
5. [Repo-structuur](#repo-structuur)
6. [Aan de slag](#aan-de-slag)
7. [Het projectmodel](#het-projectmodel)
8. [De pipeline](#de-pipeline)
9. [MCP-server](#mcp-server)
10. [Machine learning](#machine-learning)
11. [Testen en kwaliteit](#testen-en-kwaliteit)
12. [Roadmap](#roadmap)
13. [Veiligheid, AVG en aansprakelijkheid](#veiligheid-avg-en-aansprakelijkheid)
14. [Bijdragen](#bijdragen)
15. [Licentie en contact](#licentie-en-contact)

---

## Introductie

Elektriciens en installatiebedrijven besteden een groot deel van hun tijd aan werk dat zich goed laat automatiseren: tekeningen doorlezen, punten tellen, materiaallijsten en offertes opstellen en schema's tekenen. Dat is repetitief, foutgevoelig en kost veel uren voordat er één kabel getrokken is.

**ImJan** is een AI-platform dat speciaal voor de elektrotechniek is gebouwd. Het combineert:

- een **eigen vision-language model** (fine-tuned op een Qwen-basis) dat installatietekeningen begrijpt;
- **deterministische code** voor tellen, rekenen en normcontrole;
- een **MCP-server** waarmee de AI zelf echte tekeningen maakt in plaats van plaatjes te genereren.

Het uitgangspunt: **het model herkent en redeneert, de code rekent en valideert, de elektricien beslist.**

### Voor wie?

- Installatiebedrijven en zzp-elektriciens
- Calculators en werkvoorbereiders
- Tekenaars en ontwerpers in de E-installatie
- Groothandels en offerte-/ERP-leveranciers (via integraties)

---

## Wat kan het?

| Functie | Beschrijving | Status |
|---|---|---|
| **Tekeninganalyse** | Herkent symbolen, ruimtes, groepen en legenda's in DXF, IFC, vector-PDF en rasterafbeeldingen | 📋 |
| **Materiaallijsten** | Zet symbolen om naar artikelen, hoeveelheden en prijzen (ETIM-gebaseerd) | 📋 |
| **Tekenen via MCP** | AI plaatst symbolen, trekt kabelroutes en exporteert DXF/PDF | 📋 |
| **Normvalidatie** | Controleert het ontwerp op regels (o.a. NEN 1010) | 📋 |
| **Offertegeneratie** | Materiaal, arbeid en marge naar PDF-offerte | 📋 |
| **Review-UI** | Elektricien controleert en corrigeert; correcties verbeteren het model | 📋 |
| **Integraties** | Offerte-/ERP-software, groothandel-feeds, BIM | 📋 |

Legenda: ✅ klaar · 🚧 in ontwikkeling · 📋 gepland

---

## Hoe werkt het?

```
Upload (PDF / DWG / DXF / IFC / foto)
        ↓
Preprocessing (converteren, tegelen, schaal bepalen, OCR)
        ↓
Analyse-laag
  ├─ Vector parser (ezdxf / ifcopenshell)
  ├─ Symbooldetector (YOLO / RT-DETR)
  └─ Qwen-VL model (legenda, context, ruimtes, onzekere gevallen)
        ↓
Gestructureerd projectmodel (JSON / Pydantic)
        ↓
  ├─ Materiaalengine   (symbool → artikel → prijs)
  ├─ Validatie-engine  (NEN 1010 regels)
  └─ Agent-laag        (LLM + tools via MCP)
        ↓
Output: materiaallijst, offerte, DXF/PDF-tekening, rapport
        ↓
Review-UI → correcties → terug naar trainingsdata
```

### Ontwerpprincipes

1. **Hybride in plaats van alleen een model.** Vectortekeningen worden exact uitgelezen; het VLM is er voor raster en voor interpretatie.
2. **Eén bron van waarheid.** Alle onderdelen praten met hetzelfde Pydantic-projectmodel (`packages/schema`).
3. **Tellen en rekenen doet code, niet het model.**
4. **Mens in de loop.** De AI doet voorstellen, de vakman keurt goed.
5. **Elke correctie is trainingsdata.** Het systeem wordt met gebruik beter.
6. **Meten voor je verbetert.** Geen modelversie live zonder regressietest op de evaluatieset.

---

## Tech stack

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

---

## Repo-structuur

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
├── docs/
└── pyproject.toml           # uv workspace
```

---

## Aan de slag

### Vereisten

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker en Docker Compose
- Node.js 20+ en pnpm (voor de frontend)
- NVIDIA GPU met CUDA (voor model-serving en training; niet nodig voor de DXF-flow)

### Installatie

```bash
# 1. Clone de repo
git clone https://github.com/imjanai/janai.git
cd janai

# 2. Python-omgeving
uv sync

# 3. Omgevingsvariabelen
cp .env.example .env
# vul database, S3 en vLLM-gegevens in

# 4. Services starten
docker compose -f infra/docker-compose.yml up -d

# 5. Database migreren
uv run alembic upgrade head

# 6. Frontend
cd apps/web && pnpm install && pnpm dev
```

De API draait daarna op `http://localhost:8080` (docs op `/docs`) en de frontend op `http://localhost:3000`.

### Voorbeeld `.env`

```env
DATABASE_URL=postgresql+asyncpg://elektro:elektro@localhost:5432/elektro
REDIS_URL=redis://localhost:6379/0
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=elektro-uploads
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_MODEL=elektro-vl
SENTRY_DSN=
```

### Eerste analyse draaien

```bash
# Upload een DXF en start de pipeline
curl -F "file=@voorbeeld.dxf" http://localhost:8080/projects

# Haal de materiaallijst op
curl http://localhost:8080/projects/<id>/materials?format=xlsx -o materiaal.xlsx
```

---

## Het projectmodel

Alle onderdelen lezen en schrijven hetzelfde model (`packages/schema`):

```python
class Symbol(BaseModel):
    id: str
    type: SymbolType          # wandcontactdoos, schakelaar, lichtpunt, ...
    x: float                  # mm
    y: float
    room_id: str | None
    circuit: str | None       # bv. "G3"
    confidence: float = 1.0
    source: str = "vector"    # vector | detector | vlm | human

class Project(BaseModel):
    id: str
    scale: float
    rooms: list[Room]
    symbols: list[Symbol]
    warnings: list[str]
```

Dankzij dit schema kun je onderdelen los testen, vervangen of uitbreiden zonder de rest te raken.

---

## De pipeline

| # | Stap | Input → output |
|---|---|---|
| 1 | Ingest | Upload → S3 + DB-record |
| 2 | Classificatie | Bestand → type (DXF / vector-PDF / raster / IFC) |
| 3 | Normalisatie | Pagina's als PNG + vectordata, schaal bepaald |
| 4a | Vector-extractie | DXF/IFC → blokken, lagen, coördinaten |
| 4b | Detectie (raster) | PNG → bounding boxes per symbool |
| 4c | Legenda en tekst | OCR + VLM |
| 5 | VLM-redenering | Ruimtes, onzekere detecties, legenda-koppeling |
| 6 | Fusie | Alle bronnen → één `Project` |
| 7 | Validatie | `Project` → waarschuwingen |
| 8 | Materiaalengine | Symbool → artikel → hoeveelheid → prijs |
| 9 | Output | Excel, PDF-offerte, DXF |
| 10 | Review en feedback | Correcties → trainingsdata |

Elke stap is een eigen Celery-task met getypte Pydantic-input en -output.

---

## MCP-server

De MCP-server geeft een AI-agent gecontroleerde tools om echte tekeningen te maken.

| Tool | Functie |
|---|---|
| `create_drawing` | Nieuwe lege tekening aanmaken |
| `place_symbol` | Symbool (blok) plaatsen op coördinaat |
| `draw_cable` | Kabelroute als polylijn tekenen |
| `add_dimension` | Maatvoering toevoegen |
| `export_dxf` | Tekening exporteren |

Starten:

```bash
uv run python apps/mcp_server/server.py
```

Voorbeeldconfiguratie voor een MCP-client:

```json
{
  "mcpServers": {
    "imjan-draw": {
      "command": "uv",
      "args": ["run", "python", "apps/mcp_server/server.py"]
    }
  }
}
```

> **Let op:** in productie worden tekeningen opgeslagen in storage (niet in-memory) en geeft elke tool een `Project`-wijziging terug, zodat alles controleerbaar en terug te draaien is.

---

## Machine learning

### Trainingsflow

```
Labeling (CVAT / Label Studio)
   ↓ export COCO / JSONL
DVC (dataset-versies)
   ↓
Detector: Ultralytics YOLO  →  mAP per symbool
VLM: LoRA/QLoRA op Qwen-VL
   ↓
MLflow / W&B (runs en metrics)
   ↓
Evaluatie op vaste testset → alleen promoveren zonder regressie
   ↓
Export → vLLM (VLM) + ONNX/TensorRT (detector)
```

### Evaluatie

De evaluatieset (±50 tekeningen met gouden antwoorden) is heilig: nooit trainen op deze data. Per modelversie rapporteren we:

- precisie en recall per symbooltype
- afwijking in totaal aantal per symbool
- fout in uiteindelijke materiaallijst (aantal en kosten)
- percentage tekeningen dat zonder correctie door de review komt

### Feedbackloop

Correcties uit de review-UI (`POST /corrections`) komen als nieuwe voorbeelden in de dataset. Hertrainen gebeurt periodiek via een geautomatiseerde workflow, met automatische regressietest voor promotie.

---

## Testen en kwaliteit

```bash
uv run pytest            # unit- en integratietests
uv run ruff check .      # linting
uv run ruff format .     # formatting
uv run mypy .            # type checking
uv run python ml/eval/run_eval.py --model elektro-vl   # evaluatieset
```

CI (GitHub Actions) draait lint, types en tests bij elke pull request. Wijzigingen aan modellen of de pipeline moeten de evaluatieset passeren zonder regressie.

---

## Roadmap

- [ ] **Fase 0: Fundering.** Dataverzameling, projectmodel, evaluatieset, baseline.
- [ ] **Fase 1: MVP.** Upload → analyse → materiaallijst, review-UI, 3-5 pilotklanten.
- [ ] **Fase 2: Feedbackloop.** Correcties als trainingsdata, maandelijkse hertraining, prijskoppeling.
- [ ] **Fase 3: Tekenen via MCP.** Agent die schema's en installatietekeningen opbouwt.
- [ ] **Fase 4: Ontwerp en validatie.** NEN 1010-regelengine, groepsindeling, kabeldimensionering.
- [ ] **Fase 5: Schaal en integraties.** ERP/offerte, BIM/IFC, mobiele opname-app, keuringsrapporten.

---

## Veiligheid, AVG en aansprakelijkheid

- **De AI is een assistent, geen eindverantwoordelijke.** Ontwerp, dimensionering en oplevering blijven de verantwoordelijkheid van de bevoegde installateur. Dit wordt vastgelegd in de gebruiksvoorwaarden.
- **Normcontrole is regelgebaseerd.** Grenswaarden komen uit de geldende norm en worden door een domeinexpert beheerd, niet door het model bepaald.
- **Data-isolatie.** Multi-tenant met row-level security: elke klant ziet alleen eigen data.
- **AVG.** Tekeningen kunnen persoonsgegevens bevatten. Hosting in de EU, verwerkersovereenkomsten, bewaartermijnen en verwijdering op verzoek.
- **Trainingsdata.** Klantdata wordt alleen voor training gebruikt met expliciete toestemming.
- **Modellicentie.** Controleer de licentievoorwaarden van het gekozen Qwen-model voor commercieel gebruik.

---

## Bijdragen

1. Maak een branch: `git checkout -b feature/mijn-feature`
2. Schrijf tests en houd `ruff` en `mypy` schoon
3. Controleer dat de evaluatieset niet verslechtert (bij ML-wijzigingen)
4. Open een pull request met een duidelijke beschrijving

Commitberichten volgen [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, ...).

---

## Licentie en contact

© 2026 imJan AI. Alle rechten voorbehouden. Dit is propriëtaire software; neem contact op voor gebruiks- of samenwerkingsmogelijkheden.

**Contact:** Allexander Bergmans · Sander Van Praet · al@allexanderbm.be · info.sandervp@gmail.com · https://imjan.ai