# 080 — Observability

## Drie gereedschappen, drie vragen

| Tool | Vraag die het beantwoordt |
|---|---|
| **Sentry** | Wat ging er mis in de code? |
| **Prometheus + Grafana** | Hoe draait het systeem? |
| **Langfuse** | Wat doet het model, en wat kost het? |

De README noemt alle drie.

## Sentry

Vangt uitzonderingen met stacktrace, context en releasedeploy.

```python
import sentry_sdk
sentry_sdk.init(dsn=os.environ["SENTRY_DSN"], environment="productie")
```

De `SENTRY_DSN` staat al als lege variabele in de voorbeeld-`.env` van de README.

**Belangrijk:** scrub data vóór verzending. Stacktraces mogen geen klantbestandsnamen of tekening-metadata bevatten.

## Prometheus + Grafana

Wat je meet:

| Metric | Waarom |
|---|---|
| Request-latency per endpoint | Traagheid opsporen |
| Queue-lengte per queue | Onderbezetting of overvraag |
| Taakduur per pipeline-stap | Waar zit de tijd? |
| Foutpercentage per stap | Betrouwbaarheid |
| GPU-gebruik | Wanneer extra capaciteit? |
| DB-connecties en query-tijd | Blokkades |

Een metric die de business raakt:

```
projecten_per_stap{stap="6_fusie"} 42
projecten_mislukt_totaal 3
```

## Langfuse

Traceert model-aanroepen: prompt, respons, tokens, latency, kosten.

```python
from langfuse.decorators import observe

@observe
def beantwoord_vraag(afbeelding_png, vraag):
    ...
```

**Waarom dit onmisbaar is bij LLM's:** zonder traces zie je alleen "de analyse duurde 40 seconden". Met traces zie je "de legenda-aanroep vrat 8.000 tokens en leverde niets op".

### De AVG-aandachtspunt

Prompts bevatten afbeeldingen van tekeningen (als data-URI) — potentieel persoonsgegevens. Maak beleid:

- bewaartermijn beperken (bijv. 30 dagen),
- beeld-URI's weglaten in de log, alleen hashes en metadata,
- trace-export uitsluiten voor tenants die dat vragen.

Zie [084-veiligheid-en-avg](084-veiligheid-en-avg.md).

## Alarmering

| Alarm | Drempel |
|---|---|
| Foutpercentage API | > 1% over 5 min |
| Queue-lengte `vision` | > 50 voor 10 min |
| GPU-gebruik | > 95% voor 15 min |
| Database-connecties | > 80% |
| Mislukte analyses | > 5% over een dag |

## Logs

- Gestandaardiseerd (JSON), met `trace_id` en `project_id`.
- Geen stacktraces naar de gebruiker; wel een trace-id zodat support kan vinden wat er gebeurde. Zie [090-foutscenario](090-foutscenario.md).

## Wat er nu bestaat

`sentry-sdk`, `langfuse` en `mlflow` staan in [pyproject.toml](../pyproject.toml); `prometheus` nog niet. Er is geen configuratie of enige instrumentatie.
