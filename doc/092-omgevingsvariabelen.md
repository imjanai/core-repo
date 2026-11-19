# 092 — Omgevingsvariabelen

## De basis (uit de README)

```env
DATABASE_URL=postgresql+asyncpg://elektro:elektro@localhost:5432/elektro
REDIS_URL=redis://localhost:6379/0
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=elektro-uploads
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_MODEL=elektro-vl
SENTRY_DSN=
```

## Per variabele

### `DATABASE_URL`

```
postgresql+asyncpg://gebruiker:wachtwoord@host:5432/db
```

Let op het `+asyncpg`-deel: dat kiest de asynchrone driver. Zie [075-fastapi-sqlalchemy-alembic](075-fastapi-sqlalchemy-alembic.md).

### `REDIS_URL`

```
redis://host:6379/0
```

Het `/0` is het database-nummer. Voor productie met auth: `redis://:wachtwoord@host:6379/0`.

### `S3_ENDPOINT` / `S3_BUCKET`

MinIO lokaal (`http://localhost:9000`), AWS in productie (`https://s3.eu-central-1.amazonaws.com`). Ook nodig (nog niet in het voorbeeld): `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`. Zie [060-opslag-en-s3](060-opslag-en-s3.md).

### `VLLM_BASE_URL` / `VLLM_MODEL`

De interne URL van de modelserver — nooit publiek. Zie [071-model-serving-vllm](071-model-serving-vllm.md) en [018-api-grenzen](018-api-grenzen.md).

### `SENTRY_DSN`

Leeg = uit. In productie gevuld. Zie [080-observability](080-observability.md).

## Wat er nog bij moet

| Variabele | Voorbeeld | Waarom |
|---|---|---|
| `MAX_UPLOAD_MB` | `100` | Begrenzing |
| `VLM_TIMEOUT_S` | `60` | Begrenzing |
| `VLM_MAX_TOKENS` | `1024` | Kostenbeheersing |
| `DETECTION_THRESHOLD` | `0.75` | Drempel detector |
| `ENABLE_TRAINING_FEEDBACK` | `false` | Toestemmingschakelaar |
| `OIDC_ISSUER` / `OIDC_CLIENT_ID` | ... | Authenticatie |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | ... | Observability |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | MLOps |

Zie [088-secrets-en-configuratie](088-secrets-en-configuratie.md).

## Regels

1. **`.env` nooit in git.** Wel `.env.example` met dummies.
2. **Validatie bij start.** Een applicatie die begint zonder `DATABASE_URL` moet meteen duidelijk melden wat er ontbreekt, niet crashen halverwege een request.
3. **Geen defaults voor secrets.** Een fallback-wachtwoord is een lek dat op zijn beurt wacht.
4. **Per omgeving een andere set.** Dev, test en productie delen nooit secrets.

## Wat er nu bestaat

Geen `.env`, geen `.env.example`, geen validatie.
