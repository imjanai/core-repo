# 055 — De MCP-server

## Wat MCP is

**Model Context Protocol** — een open standaard (ontstaan bij Anthropic, breed overgenomen) waarmee een LLM *tools* van een externe server kan aanroepen. De agent beslist wat hij wil doen; de server bepaalt wat er mag en voert het uit.

```
AI-agent (Claude, IDE, eigen agent)
        │  MCP (stdio of HTTP)
        ▼
apps/mcp_server  ──►  packages/drawing (ezdxf)
        │
        └──► Project-wijziging terug naar de API
```

## Waarom een MCP-server in plaats van een API die de AI aanroept

| Zonder MCP | Met MCP |
|---|---|
| De AI verzint een endpoint | De tools zijn vastomlijnd |
| Onbekende acties mogelijk | Alleen de vijf tools |
| Resultaat is tekst | Resultaat is een `Project`-wijziging |
| Makkelijk te "vergeten" wat er gebeurde | Elke tool geeft een controleerbaar resultaat |

De kern: **de AI krijgt geen toegang, maar een gereedschapskist.**

## De vijf tools

| Tool | Functie |
|---|---|
| `create_drawing` | Nieuwe lege tekening aanmaken |
| `place_symbol` | Symbool (blok) plaatsen op coördinaat |
| `draw_cable` | Kabelroute als polylijn tekenen |
| `add_dimension` | Maatvoering toevoegen |
| `export_dxf` | Tekening exporteren |

Uitgebreid: [056-mcp-tools](056-mcp-tools.md).

## Starten

```bash
uv run python apps/mcp_server/server.py
```

Client-configuratie:

```json
{
  "mcpServers": {
    "imjan-draw": {
      "command": "uv",
      "args": ["run", "python", "apps/mcp_server/server.py"]
    }
  }
}
```

## De belangrijkste ontwerpregel

Uit de README:

> in productie worden tekeningen opgeslagen in storage (niet in-memory) en geeft elke tool een `Project`-wijziging terug, zodat alles controleerbaar en terug te draaien is.

Dat betekent drie dingen:

1. **Geen in-memory tekeningen.** Een crash mag niet alles weggooien; de staat hoort in storage en de database.
2. **Elke tool geeft een `Project`-diff terug**, niet alleen "oké". Zo ziet de gebruiker wat er veranderde.
3. **Terug te draaien.** Met een log van diffs kun je een reeks handelingen ongedaan maken.

Voorbeeld-antwoord:

```json
{
  "ok": true,
  "wijziging": {
    "toegevoegd": [
      {"id": "n-1", "type": "wandcontactdoos", "x": 12450.0, "y": 8300.0}
    ],
    "volgende_versie": 7
  }
}
```

## Veiligheid

De MCP-server draait potentieel op de machine van een ontwikkelaar of in een omgeving waar een externe agent toegang toe heeft. Daarom:

- **Alleen tekenen.** Geen lees-, verwijder- of beheertools voor projectdata.
- **Expliciete start.** De server draait niet standaard; iemand configureert hem.
- **Validatie van argumenten.** Coördinaten binnen een redelijk bereik, typen uit de Enum.
- **Rate limit** tegen een agent die in een lusp belandt.
- **Auditlog** van elke tool-aanroep.

Zie [089-auditlogging](089-auditlogging.md).

## Waar hij thuishoort in de roadmap

Fase 3: "Tekenen via MCP — agent die schema's en installatietekeningen opbouwt." Eerst lezen (Fase 1), dan schrijven. Zie [009-status-en-roadmap](009-status-en-roadmap.md).

## Wat er nu bestaat

[apps/mcp_server](../apps/mcp_server) is leeg; `mcp` staat in [pyproject.toml](../pyproject.toml).
