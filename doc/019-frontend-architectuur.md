# 019 — Frontendarchitectuur

## De stack

Next.js · React · TypeScript · Tailwind · shadcn/ui · PDF.js / OpenSeadragon · Konva.

## Waarom Next.js

- **Server-side rendering** voor snelle eerste weergave van projectlijsten.
- **API-routes** als BFF-laag kunnen de frontend-kant afschermen van interne endpoints.
- **TypeScript-first**, wat het delen van Pydantic-gegenereerde types met de API makkelijk maakt.

## De belangrijkste schermen

### 1. Dashboard

Projectlijst met status per tekening: `queued`, `processing (stap 4/10)`, `ready`, `needs_review`, `failed`.

### 2. Uploadschermp

Sleep-en-neer, directe upload naar S3 via presigned URL (zie [018-api-grenzen](018-api-grenzen.md)), daarna start de pipeline.

### 3. Analysescherm

Het belangrijkste scherm, en het moeilijkste:

- **Teveningenviewer**: PDF.js of OpenSeadragon voor pan/zoom op grote tekeningen.
- **Overlay**: Konva tekent de gedetecteerde symbolen bovenop het beeld, met kleur naar confidence en een legenda-knop.
- **Zijpaneel**: materiaallijst live gekoppeld aan de selectie in de tekening (klik een WCD → licht de regel op).

### 4. Reviewscherm

Per symbool: bevestigen, type wijzigen, verplaatsen, verwijderen. Elke actie wordt een correctie-object. Zie [070-feedbackloop](070-feedbackloop.md).

### 5. Offertescherm

Preview van de PDF, marge-instellingen, export.

## De tekening weergeven is het harde deel

Een installatietekening is groot (A0 of groter), bevat duizenden entiteiten en moet soepel zoomen. Daarom:

| Keuze | Reden |
|---|---|
| Gerasterd server-renderen naar tegels | Sneller dan duizenden SVG-elementen in de DOM |
| Overlay in canvas (Konva) | Symbolen blijven individueel aanpasbaar zonder DOM-cost |
| Virtuele lijst voor materiaallijst | 500 regels niet allemaal in het DOM |
| Coördinatentransformatie centraal | mm → pixel via `Project.scale`, op één plek |

De coördinatentransformatie is kritiek: het frontend-team en de pipeline moeten hetzelfde begrip van `scale` hebben. Zie [022-project-model](022-project-model.md).

## State

- Server-state (projecten, symbolen) via een query-library zoals TanStack Query.
- UI-state (geselecteerd symbool, zoomniveau) lokaal.
- Optimistic updates alleen voor correcties met rollback bij fout.

## Typen delen met de backend

Genereer TypeScript-types uit het OpenAPI-schema (`openapi-typescript` of `datamodel-code-generator` de andere kant op). Nooit handmatig overtypen — dat is precies de fout die het gedeelde schema wil voorkomen. Zie [021-schema-overview](021-schema-overview.md).

## Toegankelijkheid en taal

Nederlandstalige UI. Kleurenblindheid-vriendelijke confidence-codering (niet alleen rood/groen). Toetsenbordbediening in de review-UI omdat die uren per dag gebruikt wordt.

## Status

`apps/web` bestaat nog niet. Zie [058-web-frontend](058-web-frontend.md) en [078-frontend-stack](078-frontend-stack.md).
