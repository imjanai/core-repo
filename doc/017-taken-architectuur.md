# 017 — Takenarchitectuur (Celery)

## Waarom taken los van de API

Een analyse duurt seconden tot minuten: tegelen, meerdere model-aanroepen, parsing. Een HTTP-verzoek dat zo lang duurt, valt om (proxies, timeouts) en houdt worker-threads bezet. Daarom:

```
POST /projects  →  202 Accepted {project_id, status: "queued"}
                        │
                        ▼
               Celery-task in Redis
                        │
                        ▼
               apps/worker voert ze uit
                        │
                        ▼
               frontend pollt status / websocket
```

## Eén taak per pipeline-stap

De README stelt expliciet:

> Elke stap is een eigen Celery-task met getypte Pydantic-input en -output.

Dat betekent concreet:

```python
@celery_app.task
def stap_4a_vector_extractie(payload: NormalisatieOutput) -> VectorOutput: ...
```

### Waarom zo fijn verdeeld

| Voordeel | Effect |
|---|---|
| **Herstartbaar** | Crash bij stap 6? Opnieuw vanaf stap 6, niet opnieuw uploaden |
| **Paralleel** | 4a, 4b en 4c draaien naast elkaar |
| **Zichtbaar** | De gebruiker ziet precies waar het wacht |
| **Testbaar** | Elke stap is een functie met bekende input en output |
| **Vervangbaar** | Een andere detector? Alleen 4b aanpassen |

### Wat het vraagt

- **Idempotentie:** een stap die twee keer draait moet hetzelfde resultaat geven. Nooit halfgeschreven state nalaten.
- **Grenzen:** elke taak heeft een timeout en een maximum aantal pogingen.
- **Schoon materiaal:** geen grote binaries in de broker — die gaan naar S3, de taak draagt alleen verwijzingen.

## Volgorde en afhankelijkheden

```
1 ingest
└─► 2 classificatie
    └─► 3 normalisatie
        ├─► 4a vector-extractie ─┐
        ├─► 4b detectie ─────────┼─► 6 fusie ─► 7 validatie ─► 8 materiaal ─► 9 output
        └─► 4c tekst/legenda ───┘
                     (5 vlm-redenering voedt 6)
        …
        └─► 10 review (menselijk, niet Celery)
```

De vertakking naar 4a/4b/4c is bewust: drie onafhankelijke sporen, zie [016-hybride-aanpak](016-hybride-aanpak.md).

## Queues

Overweeg aparte queues zwaar werk niet het lichte werk laat blokkeren:

| Queue | Taken | Workers |
|---|---|---|
| `default` | 1, 2, 3, 7, 8, 9 | CPU, licht |
| `vision` | 4b, 5 | GPU |
| `parsing` | 4a, 4c | I/O-zwaar |

Zie [077-redis-en-celery](077-redis-en-celery.md).

## Monitoring en fouten

- Taakstatus zichtbaar in de API (`GET /projects/{id}` met `current_step`).
- Mislukte taak → status `failed` + foutmelding die de gebruiker kan begrijpen ("PDF is beveiligd met een wachtwoord"), niet een stacktrace.
- Sentry vangt uitzonderingen; Langfuse volgt model-aanroepen. Zie [080-observability](080-observability.md).
- Zie [090-foutscenario](090-foutscenario.md) voor de volledige foutcatalogus.

## Toekomst: Temporal?

De README noemt "later eventueel Temporal". Dat is zinvol als de workflow:

- langere, meerdere fases kent met menselijke tussenstappen, of
- strikte compensation-logging nodig heeft (bv. "reserveer prijs, dan annuleer bij falen").

Nu is Celery eenvoudiger en voldoende. Besluit pas als de pipeline stagneert op de beperkingen: geen ingebouwde workflow-log, geen first-class timers per stap. Zie [099-open-vragen](099-open-vragen.md).
