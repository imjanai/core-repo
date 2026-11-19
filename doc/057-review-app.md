# 057 — De review-app

## Wat het moet zijn

De plek waar de elektricien het voorstel van de AI beoordeelt en corrigeert. De README noemt het de **Review-UI**:

> Elektricien controleert en corrigeert; correcties verbeteren het model

## De naamgevingsverwarring

[apps/review/README.md](../apps/review/README.md) zegt "Security Reviewer". Dat is vermoedelijk een placeholder en botst met de README-structuur, die `apps/review` niet noemt maar de review-UI wel beschrijft.

**Twee interpretaties:**

| Interpretatie | Betekenis |
|---|---|
| A | `apps/review` wordt de review-UI; de titel is een placeholder |
| B | `apps/review` is iets anders (een security-reviewer voor de code) en de review-UI bestaat nog niet |

**Advies:** kies A en pas de README aan — maar leg de keuze expliciet vast, want het bepaalt waar de review-UI wordt gebouwd. Zie [099-open-vragen](099-open-vragen.md).

## Wat de gebruiker ziet

### 1. De tekening met overlay

Symbolen getekend bovenop de pagina, gekleurd naar confidence en source:

| Kleur | Betekenis |
|---|---|
| Groen | `source=vector`, confidence 1.0 |
| Blauw | detector, hoge confidence |
| Oranje | detector/vlm, lage confidence — **kijk hier** |
| Grijs | `UNKNOWN` — classificatie ontbreekt |

Zie [019-frontend-architectuur](019-frontend-architectuur.md) voor de techniek (PDF.js/OpenSeadragon + Konva).

### 2. De "twijfel-lijst"

Een gesorteerde lijst met de laagste confidences eerst. De vakman loopt die lijst af en is in vijf minuten door de plekken waar het model onzeker was. **Dit is de productiviteitswinst van de hele review.**

### 3. De materiaallijst

Live gekoppeld: klik een symbool in de tekening → licht de regel op, en omgekeerd.

### 4. De waarschuwingen

Uit de regelengine, per symbool gelinkt. Zie [047-rules-nen-1010](047-rules-nen-1010.md).

## De acties

| Actie | Correctie-object |
|---|---|
| Type wijzigen | `{veld: "type", oud, nieuw}` |
| Verplaatsen | `{veld: "x/y", oud, nieuw}` |
| Verwijderen | `{veld: "bestaat", oud: true, nieuw: false}` |
| Toevoegen | nieuwe `Symbol` met `source="human"` |
| Bevestigen | `{veld: "gecheckt", nieuw: true}` |

Elke actie wordt `POST /corrections`. Zie [053-api-endpoints](053-api-endpoints.md) en [040-stap-7-tot-10](040-stap-7-tot-10.md).

## De drie UX-regels

1. **Nooit stilzwijgend corrigeren.** Elke AI-keuze is zichtbaar en aanpasbaar.
2. **Snelheid boven schoonheid.** De vakman doet tientallen correcties per tekening; toetsenbord en dubbelklik moeten werken.
3. **Toon wat de AI niet wist.** `UNKNOWN` en lage confidence eerst — niet verstopt onder een filter.

## Waar het leert

Correcties zijn trainingsdata (met toestemming). De review-app is dus de ingang van de feedbackloop: [070-feedbackloop](070-feedbackloop.md).

## Wat er nu bestaat

Alleen [apps/review/README.md](../apps/review/README.md) ("Security Reviewer").
