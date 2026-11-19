# 058 — De web-frontend

## De stack

Next.js · React · TypeScript · Tailwind · shadcn/ui · PDF.js / OpenSeadragon · Konva.

De map [apps/web](../apps/web) bestaat nog niet.

## Waarom Next.js

- **SSR** voor snelle projectlijsten en betere SEO-vrije maar snelle eerste renders.
- **API-route-laag (BFF)** kan de browser afschermen van interne endpoints.
- **TypeScript-ecosysteem** — en het delen van typen uit het OpenAPI-schema is eenvoudig.

Alternatieven en afwegingen: [020-keuzes-en-alternatieven](020-keuzes-en-alternatieven.md).

## De schermen

| Scherm | Kern | Zie |
|---|---|---|
| Dashboard | Projecten + status per stap | [019](019-frontend-architectuur.md) |
| Upload | Drag-and-drop → presigned URL | [032](032-stap-1-ingest.md) |
| Analyse | Tekening + overlay + materiaallijst | [019](019-frontend-architectuur.md) |
| Review | Corrigeren, twijfel-lijst | [057](057-review-app.md) |
| Offerte | PDF-preview, marge, export | [040](040-stap-7-tot-10.md) |

## Het moeilijke scherm: de tekening

Een installatietekening is groot, bevat duizenden entiteiten en moet soepel zoomen. De aanpak:

1. **Server rendert tegels** (PNG per zoomniveau) — niet duizenden SVG-elementen in de DOM.
2. **Konva-canvas als overlay** voor de symbolen: individueel selecteerbaar, zonder DOM-cost.
3. **Virtuele lijst** voor de materiaallijst (500 regels).
4. **Eén coördinatentransformatie**: mm → pixel via `Project.scale`. Als frontend en backend het daarover oneens zijn, klopt niets.

## Typen delen

```bash
openapi-typescript http://localhost:8080/openapi.json -o src/api/schema.d.ts
```

Nooit met de hand overtypen: dat is precies de fout die het gedeelde schema wil voorkomen ([021-schema-overview](021-schema-overview.md)).

## State

| Soort | Waar |
|---|---|
| Server-state (projecten, symbolen) | TanStack Query |
| UI-state (selectie, zoom) | Lokaal / zustand |
| Correcties | Optimistic met rollback bij fout |

## Toegankelijkheid

De review-UI wordt uren per dag gebruikt, vaak op een tablet in de werkplaats:

- toetsenbordbediening voor de belangrijkste acties,
- contrastrijke kleuren, niet alleen rood/groen voor confidence,
- grote klikdoelen,
- offline-tolerantie voor uploads vanaf de bouwplaats (Service Worker, latere fase).

## Configuratie

De frontend praat alleen met de API (publiek) en eventueel met S3 via presigned URLs. Nooit direct met Redis, de database of vLLM. Zie [018-api-grenzen](018-api-grenzen.md).

## Wat er nu bestaat

Niets. De README noemt Node.js 20+ en pnpm als vereisten.
