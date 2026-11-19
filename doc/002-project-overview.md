# 002 — Wat imjan AI is

## Kort

**imjan AI** (geschreven `imjan`, merknaam **⚡ imjan AI**) is een AI-platform voor de elektrotechniek. Het leest installatietekeningen, herkent wat erop staat, en zet dat om in materiaallijsten, offertes, gevalideerde ontwerpen en nieuwe tekeningen.

De kernzin uit de README:

> **Het model herkent en redeneert, de code rekent en valideert, de elektricien beslist.**

Dat is geen slogan maar een architectuurkeuze: alles wat met tellen, rekenen en normcontrole te maken heeft, is deterministische Python. Het taal-/visiemodel wordt alleen ingezet waar interpretatie nodig is — begrijpen wat er op een tekening staat.

## De drie pijlers

| Pijler | Technisch | Doel |
|---|---|---|
| **Eigen vision-language model** | Qwen-VL, fijngetraind (LoRA/QLoRA) op installatietekeningen | Tekeningen begrijpen: symbolen, ruimtes, legenda's, onzekere gevallen |
| **Deterministische code** | Python-pakketten `rules`, `materials`, `parsers` | Tellen, rekenen, NEN 1010 normcontrole — reproduceerbaar |
| **MCP-server** | `apps/mcp_server` met de officiële MCP Python SDK | De AI laat echte tekeningen maken in plaats van gegenereerde plaatjes |

## Wat het concreet doet

1. Je uploadt een tekening (PDF, DWG, DXF, IFC of foto).
2. De pipeline converteert, tekent tegels, bepaalt de schaal en leest tekst uit.
3. Drie analysepaden draaien parallel: vector-parser, symbooldetector en VLM.
4. Alles vloeit samen in één gestructureerd `Project`-model (JSON/Pydantic).
5. Uit dat Project komen:
   - een **materiaallijst** (artikelen, aantallen, prijzen, ETIM-gebaseerd),
   - een **NEN 1010-validatie** met waarschuwingen,
   - een **PDF-offerte**,
   - een **DXF-tekening** die de AI zelf heeft opgebouwd.
6. De elektricien corrigeert in de review-UI. Elke correctie wordt trainingsdata.

## Wat het nadrukkelijk niet is

- Geen plaatjesgenerator: de output is gestructureerde data en echte CAD-bestanden.
- Geen eindverantwoordelijke: dimensionering en oplevering blijven bij de bevoegde installateur (zie [085](085-aansprakelijkheid.md)).
- Geen one-size-fits-all: het model is per domein (elektro) getraind, niet algemeen.

## Huidige status van de repo

De repository is vroeg in ontwikkeling. Aanwezig:

- [packages/schema](../packages/schema) — `Project`, `Symbol`, `Room`, `SymbolType` ✅
- [packages/rules/rules.py](../packages/rules/rules.py) — eerste regel: maximaal 8 WCD's per groep ✅
- [pyproject.toml](../pyproject.toml) — volledige dependency-lijst van de beoogde stack 🚧
- [ml/train_detector.py](../ml/train_detector.py) en [ml/finetune_vlm.py](../ml/finetune_vlm.py) — lege bestanden, klaar voor invulling 📋
- README's in `apps/api`, `apps/worker`, `apps/review` 📋

Nog niet aanwezig: API-code, worker-taken, MCP-server, frontend, infra, tests, docs/CI.

## Waar dit document thuishoort

Onderdeel van sectie A van de [index](001-index.md). Lees hierna [003-probleemstelling](003-probleemstelling.md) voor het *waarom*, of [011-architectuur-overview](011-architectuur-overview.md) voor het *hoe*.
