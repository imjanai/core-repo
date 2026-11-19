# 088 — Secrets en configuratie

## De voorbeeld-`.env` uit de README

```env
DATABASE_URL=postgresql+asyncpg://elektro:elektro@localhost:5432/elektro
REDIS_URL=redis://localhost:6379/0
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=elektro-uploads
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_MODEL=elektro-vl
SENTRY_DSN=
```

## De regels

1. **`.env` staat nooit in git.** Alleen `.env.example` met dummy-waarden.
2. **Lokale credentials zijn lokaal.** De dev-wachtwoorden uit het voorbeeld horen niet in productie.
3. **Productie-secrets in een secret-manager**, niet in een bestand op een server.
4. **Rotatie.** Wachtwoorden en sleutels verwisselen periodiek — en na elk vertrek van een teamlid.

## De variabelen, uitgelegd

| Variabele | Wat | Dev | Productie |
|---|---|---|---|
| `DATABASE_URL` | Postgres-verbinding | lokaal docker | managed, versleuteld wachtwoord |
| `REDIS_URL` | Celery-broker | lokaal | managed of self-hosted, met auth |
| `S3_ENDPOINT` | Objectopslag | MinIO | AWS S3, EU-regio |
| `S3_BUCKET` | Bucketnaam | `elektro-uploads` | per omgeving |
| `VLLM_BASE_URL` | Model-server | lokaal of interne IP | intern netwerk, nooit publiek |
| `VLLM_MODEL` | Modelnaam | `elektro-vl` | versie-gespecificeerd (`elektro-vl-v0.3`) |
| `SENTRY_DSN` | Foutregistratie | leeg of apart project | productie-project |

### Variabelen die er nog bij moeten

| Variabele | Waarom |
|---|---|
| `TENANT_ID_DEFAULT` | Ontwikkel-tentant |
| `MAX_UPLOAD_MB` | Begrenzing |
| `VLM_TIMEOUT_S` | Begrenzing van model-aanroepen |
| `ENABLE_TRAINING_FEEDBACK` | Toestemmingschakelaar |
| `LANGFUSE_*` | Observability |
| `JWT_SECRET` of `OIDC_*` | Authenticatie |

Zie [059-auth-en-multitenancy](059-auth-en-multitenancy.md) en [092-omgevingsvariabelen](092-omgevingsvariabelen.md).

## Waar secrets per omgeving verschillen

| Omgeving | Waar |
|---|---|
| Ontwikkeling | `.env` lokaal |
| Test | CI-secrets (GitHub Actions) |
| Productie | AWS Secrets Manager / Parameter Store |

## Een waarschuwing over logs

De meeste datalekken bij kleine teams ontstaan niet bij een hack maar bij een logregel of een screenshot in Slack. Concreet:

- log nooit een `DATABASE_URL` of een presigned URL,
- log nooit een tekening-base64,
- Sentry scrubben. Zie [080-observability](080-observability.md).

## Wat er nu bestaat

Geen `.env`, geen `.env.example`, geen secret-manager-configuratie.
