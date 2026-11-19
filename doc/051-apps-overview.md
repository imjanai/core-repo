# 051 — De vijf apps in `apps/`

## De verdeling

| App | Proces | Ingang | Status |
|---|---|---|---|
| `api` | FastAPI-backend | HTTP (publiek) | 📋 placeholder |
| `worker` | Celery-worker, de pipeline | Redis | 📋 placeholder |
| `mcp_server` | MCP-teken-tools | MCP-protocol | 📋 leeg |
| `web` | Next.js-frontend | Browser | 📋 leeg |
| `review` | Review-app (naam onzeker) | HTTP | 📋 placeholder |

## Wat ze bindt

Ze delen het `Project`-model en bevatten zo min mogelijk eigen logica. Alle domeinlogica zit in [packages](041-pakketten-overview.md).

```
web ──REST──► api ──taak──► worker ──► packages
                 │                       ▲
                 └── leest/wrijft ───────┘
agent ──MCP──► mcp_server ───────────────┘
```

## Per app de kernvragen

### `api`

- Wat is de API-surface? Zie [053-api-endpoints](053-api-endpoints.md).
- Welke authenticatie? Zie [059-auth-en-multitenancy](059-auth-en-multitenancy.md).
- Hoe publiceer je het OpenAPI-schema voor de frontend-typen? Zie [019-frontend-architectuur](019-frontend-architectuur.md).

### `worker`

- Welke taken, in welke volgorde? Zie [054-worker-celery](054-worker-celery.md).
- Hoe hervat je na een crash? Zie [017-taken-architectuur](017-taken-architectuur.md).
- Hoeveel workers, welke queues? Zie [077-redis-en-celery](077-redis-en-celery.md).

### `mcp_server`

- Welke tools krijgt de agent? Zie [056-mcp-tools](056-mcp-tools.md).
- Hoe voorkom je dat een agent onomkeerbaar tekenwerk doet? Zie [055-mcp-server](055-mcp-server.md).

### `web`

- Hoe toon je een grote tekening soepel? Zie [019-frontend-architectuur](019-frontend-architectuur.md).
- Hoe deel je typen met de API? Zie [078-frontend-stack](078-frontend-stack.md).

### `review`

- Is dit de review-UI of een security-reviewer? Zie [057-review-app](057-review-app.md).

## Waarom `review` een eigen app is

De review-UI is de plek waar het systeem leert. Hij verdient:

- eigen release-cyclus (snelle iteratie op feedback),
- een minimalistische interface die ook op een tablet in de werkplaats werkt,
- expliciete UX voor twijfelgevallen (de lijst "laagste confidence eerst").

Of het een aparte app blijft of een scherm in `web` wordt, is een open vraag. Zie [099-open-vragen](099-open-vragen.md).

## Wat er nu bestaat

Drie placeholder-README's en twee lege mappen. Zie [030-schema-verschillen-met-readme](030-schema-verschillen-met-readme.md) voor de volledige inventaris.
