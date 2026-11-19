# 004 — Voor wie is imjan AI gebouwd?

## Primaire doelgroepen

### 1. Installatiebedrijven en zzp-elektriciens

Het kernpubliek. Zij hebben:
- wisselende tekeningen van opdrachtgevers in allerlei formaten,
- geen tijd om elke plattegrond zelf uit te tellen,
- behoefte aan een materiaallijst die klopt vóór de bestelling.

**Waarde:** upload → lijst in minuten in plaats van uren.

### 2. Calculators en werkvoorbereiders

Zij vertalen tekeningen naar geld. Hun pijn:
- offertes die te hoog (verloren aanbesteding) of te laag (verlies) uitvallen,
- grote volumes, kleine marges,
- druk om snel te reageren.

**Waarde:** consistente berekeningen, herleidbaar tot de bron-tekening.

### 3. Tekenaars en ontwerpers in de E-installatie

Zij maken de tekeningen. Hun pijn:
- repetitief symbolen plaatsen en maatvoering,
- wijzigingen die alles opnieuw vragen.

**Waarde:** de AI zet het eerste ontwerp neer via MCP, de teenaar finisht. Zie [056-mcp-tools](056-mcp-tools.md).

## Secundaire doelgroepen

### 4. Groothandels

Willen materiaalvraag voorspellen of offertes koppelen aan hun assortiment. Via de materiaalengine ([048](048-materials-engine.md)) met ETIM-gebaseerde artikelkoppeling.

### 5. Offerte- en ERP-leveranciers

Integreren imjan als functionaliteit achter hun eigen scherm. Dat vraagt om stabiele API-contracten ([018-api-grenzen](018-api-grenzen.md)) en een helder datamodel ([021](021-schema-overview.md)).

### 6. BIM-coördinatoren

Gebruiken de IFC-parsing en de export terug naar open formaten.

## Waar de prioriteit ligt

| Fase | Doelgroep | Zie |
|---|---|---|
| Fase 1 (MVP) | 3–5 pilotklanten uit de primaire groep | [009-status-en-roadmap](009-status-en-roadmap.md) |
| Fase 2 | Zelfde groep, met feedbackloop | [070-feedbackloop](070-feedbackloop.md) |
| Fase 5 | Secundaire groepen via integraties | [009](009-status-en-roadmap.md) |

## Wie er bewust *niet* de doelgroep is

- **Particulieren die zelf willen klussen** — te kleine volumes, te veel uitleg nodig.
- **Bedrijven zonder bevoegde installateur** — de tool ondersteunt, maar vervangt geen bevoegdheid; zie [085-aansprakelijkheid](085-aansprakelijkheid.md).
- **Niet-elektrische disciplines** (HVAC, loodgieterij) — het symbolenset en de regels zijn elektro-specifiek. Uitbreiding is denkbaar maar geen uitgangspunt.

## Taal en regio

De README, het jargon (`wandcontactdoos`, `verdeler`, `groep`) en de norm (NEN 1010) zijn **Nederlands/Belgisch**. De eerste markt is Nederland en Vlaanderen; contact via imjan.ai. Dat beïnvloedt ook datakeuze: de trainingsset moet Nederlandse/Belgische tekeningen zijn, geen Amerikaanse symbolen.
