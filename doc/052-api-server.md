# 052 — De API-server

## De keuze

FastAPI (zoals in de README en [pyproject.toml](../pyproject.toml)).

**Let op:** [apps/api/README.md](../apps/api/README.md) zegt "FlaskAPI Server". Dat is een placeholder die niet klopt — FastAPI is de vastgelegde keuze. Zie [020-keuzes-en-alternatieven](020-keuzes-en-alternatieven.md).

## Waarom FastAPI

- **Pydantic-native.** Request- en response-modellen zijn dezelfde Pydantic-modellen als het `Project` — één taal, geen mapping-laag.
- **Async.** De API blijft snel terwijl er op database en opslag gewacht wordt.
- **OpenAPI gratis.** `/docs` levert interactieve documentatie, en het schema is de bron voor frontend-typen.
- **Validatie ingebouwd.** Ongeldige invoer wordt geweigerd vóór je code draait.

## De verantwoordelijkheden

1. Authenticatie en autorisatie (per tenant).
2. Upload-afhandeling en presigned URLs.
3. Project-status lezen en aanroepen van taken.
4. Resultaten serveren: materiaallijst, waarschuwingen, symbolen.
5. Correcties ontvangen (`POST /corrections`).
6. OpenAPI-schema publiceren.

**Wat de API níét doet:** analyseren, rekenen, modellen aanroepen. Dat hoort in de worker.

## De structuur (voorstel)

```
apps/api/
├── main.py            # app-factory, middleware, CORS
├── deps.py            # afhankelijkheden: db-session, huidige gebruiker
├── routers/
│   ├── projects.py    # upload, status, detail
│   ├── materials.py   # materiaallijst, export
│   ├── corrections.py # review-correcties
│   └── admin.py       # configuratie, catalogus
└── models/            # SQLAlchemy-tabellen
```

## Enkele ontwerpregels

### Database-sessies

Async session per request, via een dependency:

```python
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession() as session:
        yield session
```

### Tenant-scoping in de dependency

```python
async def huidige_tenant(user=Depends(huidige_gebruiker)) -> str:
    return user.tenant_id
```

Elke query krijgt `tenant_id` als filter — nooit als losse parameter die je kunt vergeten. Zie [086-multitenant-security](086-multitenant-security.md).

### Fouten

Een globale handler die interne fouten verbergt en een trace-id meelevert voor Sentry:

```json
{"detail": "Interne fout", "trace_id": "abc123"}
```

Zie [090-foutscenario](090-foutscenario.md).

### Rate limiting

Per tenant en per endpoint, met een eenvoudige token-bucket in Redis. Voorkomt dat één klant de GPU voor zichzelf opeist.

## Wat er nu bestaat

Alleen [apps/api/README.md](../apps/api/README.md) met de tekst "FlaskAPI Server".
