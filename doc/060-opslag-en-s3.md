# 060 — Opslag en S3

## De keuze

Een S3-compatibele opslag:

- **lokale ontwikkeling:** MinIO in docker-compose,
- **productie:** AWS S3 in een EU-regio (of een andere EU-provider).

Zelfde API, dus geen codeverschil: alleen `S3_ENDPOINT` verandert.

## Wat er wordt opgeslagen

| Pad | Inhoud |
|---|---|
| `uploads/<project_id>/bron.<ext>` | Het originele bestand |
| `uploads/<project_id>/pages/001.png` | Gerenderde pagina's |
| `uploads/<project_id>/tiles/...` | Tegels voor de detector |
| `intermediate/<project_id>/4a.json` | Tussenresultaten per stap |
| `exports/<project_id>/materiaal.xlsx` | Output |
| `exports/<project_id>/offerte.pdf` | Output |
| `exports/<project_id>/tekening.dxf` | Output |

## Waarom tussenresultaten in S3 en niet in de database

- Groot en semi-statisch: objectopslag is goedkoper en eenvoudiger te repliceren.
- De database houdt wat doorzocht en gerelateerd wordt.
- Tussenresultaten kun je opruimen zonder de historie te raken.

Zie [015-dataflow-eind-tot-eind](015-dataflow-eind-tot-eind.md#waar-de-data-woont).

## Uploadpaden

### Klein bestand

Browser → API → S3. Simpel, maar de API buffer het bestand.

### Groot bestand (aanbevolen)

1. `POST /projects/{id}/upload-url` → presigned PUT-URL.
2. Browser uploadt direct naar S3.
3. `POST /projects/{id}/complete` → start de pipeline.

Zie [018-api-grenzen](018-api-grenzen.md) en [032-stap-1-ingest](032-stap-1-ingest.md).

## Beveiliging

- **Bucket-policy:** geen publieke toegang, ooit.
- **Versleuteling:** server-side encryption (SSE) standaard aan.
- **Presigned URLs:** kort leven (minuten), per object.
- **Levensduur:** uploads na X maanden naar cold storage of verwijderen — afgesproken met de klant. Zie [084-veiligheid-en-avg](084-veiligheid-en-avg.md).

## MinIO lokaal

In docker-compose:

```yaml
minio:
  image: minio/minio
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: elektro
    MINIO_ROOT_PASSWORD: elektro
  ports:
    - "9000:9000"
    - "9001:9001"
```

En een bucket initialiseren (`elektro-uploads`, zie de voorbeeld-`.env` in de README).

## Integriteit

Bij het wegschrijven een SHA-256 berekenen en in de database bewaren; bij het uitlezen verifiëren. Voorkomt stille corruptie en maakt dubbele uploads herkenbaar. Zie [032-stap-1-ingest](032-stap-1-ingest.md).

## Wat er nu bestaat

Niets. `boto3` staat in [pyproject.toml](../pyproject.toml); `infra/` is leeg. Zie [079-docker-infra](079-docker-infra.md).
