# 096 — Ontwikkelwerkruimte: waar werk je aan wat?

Een overzicht voor wie een taak oppakt: waar in de repo hoor je?

## Als de taak is...

| Taak | Map |
|---|---|
| Een veld toevoegen aan het model | `packages/schema` |
| Een NEN 1010-regel schrijven | `packages/rules` |
| Een parser verbeteren | `packages/parsers` |
| De detector trainen | `ml/train_detector.py`, `ml/data` |
| Het VLM fijntrainen | `ml/finetune_vlm.py` |
| Een endpoint toevoegen | `apps/api` |
| Een pipeline-stap bouwen | `apps/worker` + het bijbehorende package |
| Een MCP-tool bouwen | `apps/mcp_server` + `packages/drawing` |
| De review-UI bouwen | `apps/review` |
| De frontend bouwen | `apps/web` |
| Docker of Terraform | `infra` |
| Documentatie | `doc` |

## De kernregel

> Logica hoort in `packages/`; processen hoort in `apps/`; modellen hoort in `ml/`.

Als je merkt dat je in `apps/api` businesslogica schrijft die niet over HTTP gaat, verplaats die naar een package. Als je in `packages/rules` een netwerkaanroep doet, hoort het in een app.

Zie [012-repo-structuur](012-repo-structuur.md) en [050-afhankelijkheidskaart](050-afhankelijkheidskaart.md).

## Welke taken elkaar blokkeren

```
(1) schema-export fixen      ── blokkeert alles in packages/
(2) eerste test              ── blokkeert vertrouwen in CI
(3) evaluatieset             ── blokkeert elk modelwerk
(4) ingest + classificatie   ── blokkeert de pipeline
(5) review-UI                ── blokkeert de feedbackloop
```

Die volgorde is de aanbevolen bouwvolgorde. Zie [030-schema-verschillen-met-readme](030-schema-verschillen-met-readme.md) en [009-status-en-roadmap](009-status-en-roadmap.md).

## Wat je zonder GPU kunt doen

Bijna alles behalve: detector trainen, VLM fijntrainen, GPU-stappen draaien. Backend, schema, regels, materialen, tekenen, frontend en documentatie vragen geen GPU. Zie [091-installatie](091-installatie.md#zonder-gpu).

## Waar je snel resultaat boekt

- **`packages/rules`** — een nieuwe regel is klein werk met directe waarde.
- **`packages/schema`** — het round-trip-testen is een half uur en voorkomt weken ellende.
- **`doc`** — documenteren wat je leert terwijl je bouwt.
