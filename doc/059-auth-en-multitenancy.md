# 059 — Authenticatie en multi-tenancy

## De eis uit de README

> **Data-isolatie.** Multi-tenant met row-level security: elke klant ziet alleen eigen data.

Twee lagen: wie ben je (authenticatie) en wat mag je zien (autorisatie).

## Authenticatie: Keycloak of Auth0

| | Keycloak | Auth0 |
|---|---|---|
| Hosting | Self-hosted (EU mogelijk) | SaaS |
| Kosten | Eigen onderhoud | Per gebruiker |
| Enterprise-features (SSO, SAML) | Ja | Ja |
| Data bij derden | Nee | Ja (relevant voor AVG) |

**Overweging:** tekeningen kunnen persoonsgegevens bevatten; een self-hosted IdP in de EU is het eenvoudigste verhaal richting klant. Maar het vraagt eigen onderhoud. Het besluit moet vallen vóór Fase 1. Zie [099-open-vragen](099-open-vragen.md) en [084-veiligheid-en-avg](084-veiligheid-en-avg.md).

## Multi-tenancy: twee modellen

| Model | Werkwijze | Pluspunt | Tegenpunt |
|---|---|---|---|
| **Shared database, RLS** | Eén Postgres, per-rij-filter | Eenvoudig, goedkoop, backup eenvoudig | Elke query moet `tenant_id` meenemen |
| Database per tenant | aparte schema/database | Sterke isolatie | Migraties × N, duurder |

De README kiest voor RLS. Dat is de juiste keuze voor dit type product.

## Row-level security in de praktijk

```sql
ALTER TABLE projecten ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolatie ON projecten
    USING (tenant_id = current_setting('app.tenant_id'));
```

En in de API:

```python
await session.execute(
    text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id}
)
```

**Waarom dit sterker is dan een filter in de code:** een vergeten `WHERE tenant_id = ...` is een datalek. Met RLS geldt het filter ongeacht wat de code doet — het zit in de database.

**Aandachtspunt:** RLS geldt per transactie. Stel `SET LOCAL` in, niet `SET`, en doe het binnen dezelfde transactie als de query.

## Wat er nog bij komt

- **Storage per tenant:** S3-prefix per tenant plus presigned URLs die alleen dat prefix raken.
- **Redis:** namespaces per tenant voor caches.
- **ML-inferentie:** het model ziet klantdata; leg vast hoe lang die in logs blijft. Zie [080-observability](080-observability.md).

## Rollen

| Rol | Mag |
|---|---|
| `admin` | Instellingen, gebruikers, catalogus |
| `calculator` | Projecten, materiaallijsten, offertes |
| `monteur` | Review, correcties |
| `lezer` | Alleen bekijken |

Implementeer als rollen in het token, gecontroleerd per endpoint.

## Wat er nu bestaat

Niets. `asyncpg` staat in [pyproject.toml](../pyproject.toml).
