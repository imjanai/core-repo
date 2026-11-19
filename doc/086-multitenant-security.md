# 086 — Multi-tenant security

## De eis

> **Data-isolatie.** Multi-tenant met row-level security: elke klant ziet alleen eigen data.

## Waarom RLS in plaats van filters in code

Een `WHERE tenant_id = ...` in elke query is een belofte die je niet kunt controleren. Eén vergeten filter is een datalek waarbij klant A de tekeningen van klant B ziet.

RLS zit in de database en geldt ongeacht wat de code doet.

```sql
ALTER TABLE projecten ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolatie ON projecten
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

## Hoe de tenant wordt ingesteld

```python
async def met_tenant(tenant_id: str, session: AsyncSession):
    await session.execute(
        text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id}
    )
```

**Kritiek:** `SET LOCAL`, niet `SET`. `SET` blijft aan de verbinding plakken en kan de volgende gebruiker de data van de vorige geven. `SET LOCAL` geldt alleen binnen de transactie.

## De volledige checklist

| Laag | Maatregel |
|---|---|
| **Auth** | Token bevat `tenant_id`; nooit uit de request body. Zie [059](059-auth-en-multitenancy.md) |
| **API** | Tenant-scoping via dependency, niet per endpoint |
| **Database** | RLS op alle tabellen met klantdata |
| **Storage** | Prefix per tenant; presigned URLs per object |
| **Cache** | Namespace per tenant (Redis-key-prefix) |
| **Logs** | `tenant_id` in elke logregel; geen bestandsnamen in traces |
| **Backups** | Herstel per tenant mogelijk |
| **Model** | Traces en caching bevatten geen klantafbeeldingen buiten de tenant |

## De veelgemaakte fouten

1. **RLS vergeten op een nieuwe tabel.** Elke migratie die een tabel toevoegt, moet ook een policy toevoegen. Maak daar een checklist-item van in [083-cicd](083-cicd.md).
2. **`SET LOCAL` buiten de transactie.** Dan werkt het niet en valt alles open.
3. **Bypass door superuser.** Postgres-superusers en table-owners omzeilen RLS standaard. Gebruik voor de applicatie een aparte rol.
4. **Presigned URL's die te breed zijn.** Een URL op bucketniveau geeft alles weg; op objectniveau is het veilig.
5. **Celery-taken zonder tenant.** De taak krijgt `project_id` en leest de tenant uit de DB — nooit de tenant uit de taakargumenten overnemen.

## Testen

Schrijf een integratietest die bewijst dat isolatie werkt:

```python
async def test_tenant_ziet_niet_anders_project():
    await maak_project(tenant="a", naam="geheim")
    resultaat = await haal_project(tenant="b", id=...)
    assert resultaat is None
```

Zonder die test is RLS een aanname. Zie [081-teststrategie](081-teststrategie.md).

## Wat er nu bestaat

Niets. Er is geen database, geen tabel, geen policy.
