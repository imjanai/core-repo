# 032 — Stap 1: Ingest

## Wat er gebeurt

De gebruiker dropt een bestand. In minder dan een seconde terug:

- het bestand staat veilig in S3,
- er is een database-record,
- er is een taak gestart,
- de gebruiker ziet "in wachtrij".

## De request

```http
POST /projects
Content-Type: multipart/form-data

file=@tekening.dxf
```

Antwoord (202 Accepted):

```json
{
  "id": "0f6b1e2a-...",
  "status": "queued",
  "created_at": "2026-10-12T09:14:02Z"
}
```

## Wat de API doet

1. **Auth-controle** — is dit token geldig, en hoeveel projecten mag deze tenant hebben?
2. **Bestandscontrole** — extensie in de allowlist (`.dxf .dwg .ifc .pdf .png .jpg .jpeg .webp`), mimetype, grootte (max 100 MB?).
3. **Viruscan** — ClamAV of vergelijkbaar vóór opslag. Tekeningen komen van buiten.
4. **S3-put** — weggeschreven onder `uploads/<project_id>/<naam>`.
5. **DB-insert** — `ProjectRecord` met `status="queued"`.
6. **Taakstart** — `stap_2_classificatie.delay(project_id)`.

## Ontwerpregels

### Upload via presigned URL

Voor grote bestanden: de API geeft een presigned URL, de browser uploadt direct naar S3, en de API start pas na een `POST /projects/{id}/complete` de pipeline. Dit voorkomt dat de API gigabytes door zichzelf heen moet sluizen. Zie [018-api-grenzen](018-api-grenzen.md).

### Idempotentie

Een dubbele upload (netwerkfout, opnieuw drukken) mag geen tweede project aanmaken. Gebruik een client-generated idempotency-key of vergelijk de hash van het bestand.

### Wat ingest níet doet

Geen parsing, geen formaatherkenning verder dan de extensie, geen schaalbepaling. Houdt de stap klein en herhaalbaar.

## Datastructuur

```python
class ProjectRecord(BaseModel):
    id: str
    tenant_id: str
    filename: str
    size_bytes: int
    sha256: str
    status: str            # queued | processing | ready | needs_review | failed
    current_step: int | None
    created_at: datetime
    updated_at: datetime
```

`sha256` dient dubbele-detectie en integriteitscontrole: bij het uitlezen uit S3 kun je verifiëren dat het bestand niet beschadigd is.

## Randgevallen

| Randgeval | Gedrag |
|---|---|
| Bestand > limiet | 413 met begrijpelijk bericht |
| Onbekende extensie | 415, met suggestie van toegestane formaten |
| DWG | Accepteren en in stap 3 via ODA Converter naar DXF zetten |
| Beveiligd PDF | Pas in stap 2/3 gedetecteerd; foutmelding terug naar gebruiker |
| Leeg bestand | 400 direct |
| ZIP | Niet accepteren in MVP (extractie-attacks) |

## Wat er nu bestaat

Niets. `apps/api` bevat alleen een placeholder-README. Zie [052-api-server](052-api-server.md).
