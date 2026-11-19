# 054 — De Celery-worker

## De rol

[apps/worker](../apps/worker) is waar de pipeline draait: één proces dat taken uit Redis ophaalt en uitvoert. Al het zware werk gebeurt hier — parsing, GPU-aanroepen, export.

De README in de map zegt het al:

> Celery tasks (de pipeline)

## De taken

```python
# apps/worker/tasks.py
@celery_app.task(bind=True, max_retries=3)
def stap_1_ingest(self, project_id: str): ...
@celery_app.task
def stap_2_classificatie(project_id: str): ...
@celery_app.task
def stap_3_normalisatie(project_id: str): ...
@celery_app.task
def stap_4a_vector_extractie(project_id: str): ...
@celery_app.task
def stap_4b_detectie(project_id: str): ...
@celery_app.task
def stap_4c_tekst_en_legenda(project_id: str): ...
@celery_app.task
def stap_5_vlm_redenering(project_id: str): ...
@celery_app.task
def stap_6_fusie(project_id: str): ...
@celery_app.task
def stap_7_validatie(project_id: str): ...
@celery_app.task
def stap_8_materiaal(project_id: str): ...
@celery_app.task
def stap_9_output(project_id: str): ...
```

## Ontwerpregels

### 1. Alleen `project_id` als argument

Geen grote objecten door de broker slepen — dat vertraagt alles. De taak leest de staat uit de database en S3.

### 2. Elke taak zet `current_step` en `status`

Zodat de frontend kan tonen waar het proces is, en een fout begrijpelijk is.

### 3. Idempotentie

Elke taak mag twee keer draaien zonder schade. Concreet:

- schrijf resultaten naar een bekende sleutel (overschrijven, niet appenderen),
- gebruik transities: alleen starten als `status` het toelaat.

### 4. Chord voor de vertakking

```python
chord(
    [stap_4a.s(pid), stap_4b.s(pid), stap_4c.s(pid)],
    stap_5_vlm_redenering.s(pid),
)()
```

De drie sporen parallel, daarna de redenering. Zie [017-taken-architectuur](017-taken-architectuur.md).

### 5. Begrenzingen

```python
task_time_limit = 600        # hard stop
task_soft_time_limit = 540    # kans om op te ruimen
```

Een vastgelopen VLM-aanroep mag de worker niet blijven bezet houden.

### 6. Zware modellen één keer laden

Een detector of OCR-model per taak laden kost seconden. Laad het bij worker-start (via een `@worker_ready`-signal) en houd het in geheugen.

## Deploy

Een aparte container/`replica` van de API:

```yaml
worker:
  build: .
  command: uv run celery -A apps.worker worker -Q vision,parsing,default
  deploy:
    replicas: 2
  depends_on:
    - redis
    - vllm
```

De GPU-queue (`vision`) krijgt een eigen worker-pool zodat zwaar werk het lichte niet blokkeert. Zie [077-redis-en-celery](077-redis-en-celery.md).

## Monitoring

- `celery inspect active` voor debugging.
- Flower (optioneel) of een eigen endpoint dat `GET /projects/{id}` voedt.
- Queue-lengte als Prometheus-metric — het eerste signaal dat er te weinig workers draaien. Zie [080-observability](080-observability.md).

## Wat er nu bestaat

Alleen [apps/worker/README.md](../apps/worker/README.md).
