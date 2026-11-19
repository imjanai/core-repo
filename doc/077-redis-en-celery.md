# 077 — Redis en Celery

## De rollen

| | Wat |
|---|---|
| **Redis** | Broker (taken wachten hier) + resultaten + cache |
| **Celery** | Taakframework: taken definiëren, plannen, retryen |

De README:

> **Taken:** Celery + Redis (later eventueel Temporal)

## Waarom Redis

- Snel, in-geheugen.
- Volwassen ondersteuning in Celery.
- Dubbele rol: broker én cache (bv. rate limits, presigned-URL-geheugen).

**Aandachtspunt:** Redis is standaard geen duurzame opslag. Voor taken die niet verloren mogen gaan, zet je persistence aan (`appendonly yes`) of je accepteert dat een herstart taken opnieuw laat uitvoeren — wat dankzij idempotentie veilig is. Zie [017-taken-architectuur](017-taken-architectuur.md).

## Queues

Eén queue voor alles werkt, tot de eerste zware analyse het lichte werk blokkeert.

| Queue | Taken | Worker |
|---|---|---|
| `default` | 1, 2, 3, 6, 7, 8, 9 | CPU, licht |
| `parsing` | 4a, 4c (OCR) | I/O-zwaar |
| `vision` | 4b, 5 (GPU) | GPU-worker |

```bash
uv run celery -A apps.worker worker -Q vision,parsing,default
```

De GPU-worker heeft een klein aantal processen (de GPU is het knelpunt); de CPU-worker mag breder.

## Retry en timeouts

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    soft_time_limit=540,
    time_limit=600,
)
def stap_5_vlm_redenering(self, project_id: str):
    try:
        ...
    except VLMFout as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

- **Exponentiële backoff** voorkomt dat een haperende GPU direct opnieuw wordt bestormd.
- **Soft limit** geeft de taak kans om op te ruimen; **hard limit** knipt af.
- **Fouten naar de gebruiker:** een mislukte taak zet `status="failed"` met een begrijpelijk bericht, niet een stacktrace. Zie [090-foutscenario](090-foutscenario.md).

## Monitoring

- Queue-lengte als metric — het eerste signaal van onderbezetting.
- Taakduur per stap — waar zit de tijd?
- Foutpercentage per stap.

Zie [080-observability](080-observability.md). Flower is een optionele web-UI; een eigen endpoint op `GET /projects/{id}` is vaak genoeg.

## Wanneer Temporal?

De README noemt het als toekomstige optie. Stap over als:

- de workflow langere, opgeslagen fases met menselijke tussenstappen krijgt,
- je compensation-logging nodig hebt (bv. "reserveer prijs, annuleer bij falen"),
- takenketens zo complex worden dat de Celery-chord-onderhoud onduidelijk wordt.

Zie [017-taken-architectuur](017-taken-architectuur.md#toekomst-temporal).

## Wat er nu bestaat

Niets. `celery[redis]` staat in [pyproject.toml](../pyproject.toml).
