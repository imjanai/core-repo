# 053 — API-endpoints (voorstel)

Dit is een **voorstel**, geen bestaande implementatie. Het dient als startpunt voor [apps/api](../apps/api).

## Projecten

### `POST /projects`

Upload starten.

```
multipart/form-data: file
```

→ `202 Accepted`

```json
{"id": "…", "status": "queued", "current_step": null}
```

Fouten: `413` te groot, `415` formaat niet ondersteund, `429` quota.

### `GET /projects`

Lijst van projecten van de huidige tenant, gepagineerd.

Query: `?status=needs_review&page=1&size=20`

### `GET /projects/{id}`

Status en samenvatting.

```json
{
  "id": "…",
  "status": "processing",
  "current_step": 4,
  "step_name": "Detectie (raster)",
  "warnings": [],
  "counts": {"symbols": 0, "rooms": 0}
}
```

### `DELETE /projects/{id}`

Verwijderen incl. opslag. Retentiebeleid toepassen. Zie [084-veiligheid-en-avg](084-veiligheid-en-avg.md).

## Symbolen en tekening

### `GET /projects/{id}/symbols`

```json
[{"id": "…", "type": "wandcontactdoos", "x": 12450.0, "y": 8300.0,
  "room_id": "r1", "circuit": "G3", "confidence": 1.0, "source": "vector"}]
```

Query: `?min_confidence=0.8&circuit=G3`

### `GET /projects/{id}/rooms`

Ruimtes met polygonen.

### `GET /projects/{id}/page/{n}.png`

Gerenderde pagina voor de viewer (of een presigned URL).

## Materiaal en output

### `GET /projects/{id}/materials`

```json
{"lines": [{"artikelnummer": "WCD-86-RVS", "aantal": 24,
            "stuksprijs": 8.4, "regelprijs": 201.6}]}
```

### `GET /projects/{id}/materials?format=xlsx`

Binary export (Excel).

### `GET /projects/{id}/quote?format=pdf`

PDF-offerte.

### `GET /projects/{id}/drawing.dxf`

DXF-export.

## Validatie

### `GET /projects/{id}/warnings`

```json
[{"rule_id": "grp-wcd", "severity": "warn",
  "message": "Groep G3 heeft 12 WCD's (controleer belasting)",
  "symbol_ids": ["…"]}]
```

## Review en correcties

### `POST /projects/{id}/corrections`

```json
{"symbol_id": "…", "veld": "type", "oud": "lichtpunt",
 "nieuw": "wandcontactdoos", "reviewer": "user-1"}
```

Deze endpoint voedt de feedbackloop — zie [070-feedbackloop](070-feedbackloop.md).

### `POST /projects/{id}/symbols`

Handmatig een gemist punt toevoegen.

### `DELETE /projects/{id}/symbols/{sid}`

Valse positie verwijderen.

## Export van het schema

### `GET /openapi.json`

Bron voor frontend-typen. Zie [019-frontend-architectuur](019-frontend-architectuur.md).

## Versiebeheer

Vanaf het moment dat externe partijen zich aansluiten: alles onder `/v1/`. Toevoegen mag; brekend pas na een migratieperiode. Zie [018-api-grenzen](018-api-grenzen.md).

## Authenticatie

Alle endpoints behalve `/healthz` vragen om een Bearer-token; `tenant_id` komt uit het token, nooit uit de request. Zie [059-auth-en-multitenancy](059-auth-en-multitenancy.md).
