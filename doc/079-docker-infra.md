# 079 — Docker en infrastructuur

## De map

[infra](../infra) moet bevatten (volgens de README):

```
infra/
├── docker-compose.yml      # lokaal: alle services
├── docker-compose.prod.yml # productie-overlay
└── terraform/              # cloud-resources
```

De map is nu leeg.

## De services in docker-compose

| Service | Image | Poort |
|---|---|---|
| `api` | eigen build | 8080 |
| `worker` | eigen build | — |
| `web` | eigen build (Next.js) | 3000 |
| `postgres` | `postgres:16` | 5432 |
| `redis` | `redis:7` | 6379 |
| `minio` | `minio/minio` | 9000, 9001 |
| `vllm` | `vllm/vllm` (GPU) | 8000 |

Een grove schets:

```yaml
services:
  api:
    build: .
    command: uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8080
    env_file: .env
    ports: ["8080:8080"]
    depends_on: [postgres, redis, minio]

  worker:
    build: .
    command: uv run celery -A apps.worker worker -Q vision,default
    env_file: .env
    depends_on: [redis, vllm]

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: elektro
      POSTGRES_PASSWORD: elektro
      POSTGRES_DB: elektro
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]

volumes:
  pgdata:
```

## De GPU-vraag

vLLM en de detector hebben CUDA nodig:

```yaml
  vllm:
    image: vllm/vllm:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Zonder GPU kun je de hele stack behalve `vllm` draaien — handig voor backend-ontwikkeling. Documenteer dat in de README, zodat niet iedereen een GPU denkt te moeten hebben.

## Dev versus productie

| | Dev | Productie |
|---|---|---|
| Opslag | MinIO lokaal | AWS S3, EU-regio |
| Database | docker volume | Managed Postgres, backups |
| vLLM | lokaal, optioneel | Eigen instance of managed |
| Secrets | `.env` | Secret-manager (bv. AWS Secrets Manager) |
| Terrafom | niet nodig | Wel — infra als code |

## Terraform

Voor productie: VPC, RDS, S3, GPU-instances, DNS, TLS. In een aparte map met state in een remote backend (nooit lokaal in git).

**Waarom infra als code:** een handmatig opgezette omgeving is niet reproduceerbaar en niet auditbaar. Bij een AVG-audit moet je kunnen tonen hoe de omgeving is ingericht.

## Wat er nu bestaat

Niets. [infra](../infra) is leeg; er is geen docker-compose en geen Terraform.
