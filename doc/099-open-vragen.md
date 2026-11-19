# 099 — Open vragen

Beslissingen die nog niet gevallen zijn, met de opties en wat ze beïnvloeden.

## Technisch

### 1. `doc/` of `docs/`?

De README-structuur noemt `docs/`; deze map heet `doc/`.

- **`docs/`**: volgt de conventie en de README.
- **`doc/`**: korter, maar botst met de README.

**Beïnvloedt:** niets functioneels; wel de verwarring van nieuwe bijdragers.

### 2. `apps/review` — review-UI of security-reviewer?

De map zegt "Security Reviewer"; de README beschrijft een review-UI.

- **A:** `apps/review` wordt de review-UI; placeholder aanpassen.
- **B:** Beide apart; de review-UI krijgt een eigen map.

**Beïnvloedt:** waar de belangrijkste schermen van Fase 1 gebouwd worden. Zie [057-review-app](057-review-app.md).

### 3. Import-structuur: workspace-pakketten of PYTHONPATH?

De huidige `from schema import Project` werkt niet. Opties:

- Workspace-pakketten met `imjan-schema` (aanbevolen), of
- `from packages.schema import Project` met package-`__init__.py`'s.

**Beïnvloedt:** elke import in het project. Zie [026-schema-export](026-schema-export.md).

### 4. JSONB of ge-normaliseerde tabellen?

Voor het opslaan van `Project` in Postgres.

**Beïnvloedt:** query-prestaties, migraties, de API-laag. Zie [076-postgres-pgvector](076-postgres-pgvector.md).

### 5. IdP: Keycloak of Auth0?

Zelf gehost versus SaaS; AVG-overwegingen.

**Beïnvloedt:** Fase 1 met pilotklanten. Zie [059-auth-en-multitenancy](059-auth-en-multitenancy.md).

### 6. Licentie van Ultralytics en PyMuPDF

Beide zijn AGPL of commercieel. Voor een proprietary SaaS kan AGPL verplichtingen meebrengen.

**Beïnvloedt:** de hele stackkeuze; moet juridisch beoordeeld worden vóór Fase 1. Zie [087-modellicenties](087-modellicenties.md).

### 7. Celery of Temporal?

Nu Celery; Temporal als workflows complexer worden. Zie [017-taken-architectuur](017-taken-architectuur.md#toekomst-temporal).

### 8. `Symbol.rotation` erbij?

Nodig voor tekenen via MCP; vraagt labelwerk. Zie [023-symbol-model](023-symbol-model.md) en [029-schema-uitbreiden](029-schema-uitbreiden.md).

### 9. `UNKNOWN` als `SymbolType`?

Een vangnet voor onbekende detecties. Zie [025-symboltype-enum](025-symboltype-enum.md#over-unknown).

## Product

### 10. Welke tekening eerst: DXF of PDF?

- **DXF:** betrouwbaar, direct waarde, geen GPU.
- **PDF:** groter volume in de praktijk.

**Advies:** DXF eerst, om de keten te bewijzen; PDF volgt. Zie [016-hybride-aanpak](016-hybride-aanpak.md#praktische-consequentie-voor-de-mvp).

### 11. Eén land of twee?

Nederland en Vlaanderen hebben verschillende gewoontes en materiaal. Beginnen met één vereenvoudigt de catalogus en de regels.

### 12. Welke groothandel eerst?

De materiaalcatalogus komt ergens vandaan. Eén leverancier met een API versnelt Fase 1 aanzienlijk.

## Compliance

### 13. Bewaartermijnen

Concrete getallen, afgestemd met pilotklanten. Zie [084-veiligheid-en-avg](084-veiligheid-en-avg.md#3-bewaartermijnen).

### 14. Toestemmingsflow

Hoe vraag je toestemming voor training zonder de gebruiker te vertragen? Zie [070-feedbackloop](070-feedbackloop.md#2-toestemming-controleren).

## Hoe beslissen?

Voor elk onderwerp: opties opschrijven, een datum zetten, beslissen. Beslissingen die blijven liggen zijn duurder dan imperfecte keuzes — vooral nu de codebasis klein is.
