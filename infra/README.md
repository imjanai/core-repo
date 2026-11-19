# infra — lokale stack

Eén commando draait de volledige keten (Postgres, Redis, MinIO, API,
Celery-worker en Celery-beat) lokaal:

```bash
docker compose -f infra/docker-compose.yml up --build -d
```

* API + OpenAPI-docs: http://localhost:8080/docs
* MinIO-console: http://localhost:9001 (minioadmin / minioadmin)

De API voert bij het starten `alembic upgrade head` uit; worker en beat
starten pas als de API gezond is (en dus de tabellen bestaan). De sweeper
draait in deze stack elke 20 seconden (`STALE_CHECK_SECONDS`) zodat
herstelgedrag snel waarneembaar is; de productiewaarde (300 s) staat in
`apps/api/core/config.py`.

## End-to-end verifiëren

Met de stack draaiend:

```bash
bash infra/e2e-stack-check.sh
```

Het script bewijst vier dingen tegen de echte HTTP-, broker- en
databasegrenzen (geen mocks):

1. **Upload → analyse → succes.** Genereert een DXF in de api-container,
   uploadt hem, pollt `GET /projects/{id}/pipeline` tot `succeeded` en
   controleert dat symbolen én materialen berekend zijn.
2. **Sweeper geeft op.** Zaait een gestrande run met het maximum aan
   hervatpogingen; de sweeper markeert die definitief als `failed` met de
   melding "handmatige inspectie vereist".
3. **Handmatig hervatten.** Zaait een gefaalde run, roept
   `POST .../pipeline/resume` aan (verwacht 202 + taak-id) en ziet dezelfde
   run alsnog voltooien.
4. **Sweeper herstelt.** Zaait een verse gestrande run; de sweeper pakt die
   automatisch op en de run eindigt als `succeeded`.

Stoppen en opruimen (behoudt de volumes):

```bash
docker compose -f infra/docker-compose.yml down
```

## Bekende aandachtspunten

* **Groot beeld.** `uv sync --frozen` installeert álle lockfile-dependencies,
  inclusief torch met CUDA-wheels voor Linux: reken op enkele GB's download
  bij de eerste build. Het beeld is bewust de lockfile-getrouwe variant;
  opdelen in dependency-groepen is een vervolgstap.
* **MinIO-healthcheck** gebruikt `curl` in de minio-image; zie je die
  healthcheck falen terwijl de console bereikbaar is, vervang de check dan
  door `mc ready local`.
* **vLLM/GPU** zit er bewust niet in — de `vlm`-stage is optioneel en wordt
  overgeslagen zonder vLLM-endpoint.
