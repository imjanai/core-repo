# 089 — Auditlogging

## De vraag

Als er iets misgaat — een verkeerde materiaallijst, een datalek, een klant die vraagt "wie heeft mijn tekening bekeken?" — moet je het antwoord kunnen geven.

## Wat wordt gelogd

| Gebeurtenis | Wat vastleggen |
|---|---|
| **Inloggen** | wie, wanneer, IP, succes |
| **Upload** | wie, welk project, bestandsnaam, hash |
| **Analyse gestart** | project, modelversie, stappen |
| **Resultaat bekeken** | wie, welk project, welk formaat |
| **Correctie** | wie, welk symbool, oud → nieuw |
| **Export** | wie, welk project, welk bestand |
| **Verwijderen** | wie, welk project, wat er verwijderd werd |
| **Toestemming** | wie, wanneer, wat, ingetrokken op |

## Het model

```python
class AuditLog(BaseModel):
    id: str
    tijdstip: datetime
    tenant_id: str
    actor: str                 # gebruiker of "systeem"
    actie: str                 # enum
    object_type: str           # project | symbool | export
    object_id: str
    details: dict              # beperkt; geen grote payloads
    trace_id: str | None
```

## De regels voor auditlogs

1. **Append-only.** Nooit bijwerken of verwijderen binnen de retentie.
2. **Geen payloads.** Log de actie, niet de inhoud van de tekening of de prompt.
3. **Beperkte retentie.** Auditlogs zelf zijn ook persoonsgegevens (wie deed wat); bewaar ze niet eindeloos.
4. **Per tenant doorzoekbaar.**
5. **Niet in de primaire database als die krap is** — aparte tabel of aparte opslag.

## Wat de MCP-server extra moet loggen

Elke tool-aanroep van een agent is een handeling namens de gebruiker:

```json
{"actie": "mcp.place_symbol", "project_id": "…",
 "argumenten": {"type": "wandcontactdoos", "x": 12450, "y": 8300}}
```

Zonder dat zie je achteraf niet wat een agent gedaan heeft — en een agent die in een lusp belandt, laat sporen na. Zie [055-mcp-server](055-mcp-server.md).

## Wat er nu bestaat

Niets. Er is geen database en geen logging.
