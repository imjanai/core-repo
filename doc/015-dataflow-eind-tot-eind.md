# 015 — Dataflow van eind tot eind

Het volledige pad van een bestand op de laptop van de gebruiker tot een materiaallijst in Excel, met de datastructuur op elk punt.

## Stap voor stap met datastructuren

```
1.  gebruiker kiest bestand
      → bytes (multipart/form-data)

2.  POST /projects
      → S3-object: uploads/<project_id>/bron.dxf
      → DB-row: ProjectRecord(id, status="pending", tenant_id)

3.  classificatie
      → bestandstype: "dxf" | "vector_pdf" | "raster" | "ifc"

4.  normalisatie
      → pagina's: uploads/<id>/pages/001.png ... (raster)
      → vectordata: uploads/<id>/vectors.json        (vector)
      → schaal: 100.0 (mm per eenheid)

5a. vector-extractie (dxf/ifc)
      → list[VectorSymbol]  {layer, block_name, x, y, rotatie}

5b. detectie (raster)
      → list[Detection]  {klasse="wandcontactdoos", bbox, confidence=0.93}

5c. tekst en legenda (ocr + vlm)
      → list[TextSpan] {tekst, bbox}
      → LegendaMapping {symboolbeeld → type-naam}

6.  vlm-redenering
      → list[RoomProposal] {polygon, naam="Woonkamer"}
      → list[Reinterpretatie] {detectie_id, nieuwe_type, reden}

7.  fusie
      → Project {
            id, scale,
            rooms:  [Room{id, name, polygon}],
            symbols:[Symbol{id, type, x, y, room_id, circuit,
                            confidence, source}],
            warnings: [...]
        }                                        ← packages/schema

8.  validatie (rules)
      → warnings: ["Groep G3 heeft 12 WCD's (controleer belasting)"]

9.  materiaalengine
      → list[MaterialLine] {artikelnummer, omschrijving, aantal,
                            stuksprijs, regelprijs}

10. output
      → materiaal.xlsx  (openpyxl)
      → offerte.pdf     (Jinja2 + WeasyPrint)
      → tekening.dxf    (ezdxf)

11. review
      → list[Correction] {symbol_id, veld, oud, nieuw, reviewer}
      → trainingsset (na toestemming)
```

## Waar de data woont

| Moment | Locatie |
|---|---|
| Bronbestand | S3 |
| Pagina's, tegels | S3 |
| Tussenresultaten per stap | S3 + DB-status |
| Gefuseerd `Project` | PostgreSQL (JSONB of ge-normaliseerd) |
| Embeddings (zoeken/deduplicatie) | PostgreSQL + pgvector |
| Correcties | PostgreSQL, gekoppeld aan `project_id` |
| Trainingsset | DVC-repository (`ml/data`) |

## Waarom niet alles in de database

Tegels en paginarenders zijn groot en semi-statisch: objectopslag is goedkoper en eenvoudiger te repliceren. De database houdt wat je doorzoekt en relateert. Die scheiding houdt backups klein en queries snel.

## Identiteit en herleidbaarheid

Elk symbool krijgt een stabiele `id`. Die id is de sleutel waarmee:

- de reviewer zijn correctie vastlegt,
- de trainingsset aan het bronbeeld gekoppeld blijft,
- regressies te herleiden zijn naar een specifieke detectie.

**Regel:** id's worden bij fusie vastgelegd en nooit gewijzigd, ook niet als een latere stap het type corrigeert. Zie [039-stap-6-fusie](039-stap-6-fusie.md).

## Asynchrone aard

Elk punt tussen 2 en 10 is een Celery-taak. De gebruiker ziet "in wachtrij → stap X van 10". Bij crash herstart de pipeline bij de laatste succesvolle stap, niet bij nul. Zie [017-taken-architectuur](017-taken-architectuur.md) en [090-foutscenario](090-foutscenario.md).
