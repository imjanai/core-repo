# 078 — De frontend-stack

## De onderdelen

| Tool | Rol |
|---|---|
| **Next.js** | Framework, routing, SSR |
| **React** | UI-bouwstenen |
| **TypeScript** | Typen, compilecontrole |
| **Tailwind** | Utility-CSS, snel ontwerpen |
| **shadcn/ui** | Toegankelijke componenten, bron in jouw repo |
| **PDF.js** | PDF weergeven in de browser |
| **OpenSeadragon** | Deep-zoom viewer voor grote beelden |
| **Konva** | Canvas-overlay voor interactieve symbolen |

## shadcn/ui — waarom geen componentbibliotheek

shadcn is geen package die je importeert; het kopieert componentcode naar je repo. Voordelen:

- **Geen vendor-lock** — het component is van jou, aanpasbaar zonder op upgrades te wachten.
- **Toegankelijkheid ingebouwd** — focus-state, keyboard, ARIA.
- **Tailwind-native** — past in de rest van de styling.

Voor een review-UI die uren per dag gebruikt wordt, is die controle belangrijk.

## De tekening weergeven

### PDF.js

Rendert PDF in de browser, inclusief tekstlaag. Goed voor zoeken en selecteren.

### OpenSeadragon

Deep-zoom: tegels op meerdere zoomniveaus, soepel pannen op grote tekeningen. Ideaal voor A0- en A1-formaten.

### Konva

Een canvas-laag bovenop de viewer, waarin de symbolen worden getekend en geselecteerd. Voordelen ten opzichte van DOM-elementen:

- duizenden symbolen zonder performance-piek,
- eenvoudig roteren, schalen, transformeren,
- bewerken door slepen (verplaatsen van een symbool).

### De coördinatentransformatie

Eén centrale functie die mm → pixels omrekent met `Project.scale`. Als frontend en backend het daarover oneens zijn, klopt niets. Zie [022-project-model](022-project-model.md) en [019-frontend-architectuur](019-frontend-architectuur.md).

## Typen uit het OpenAPI-schema

```bash
openapi-typescript http://localhost:8080/openapi.json -o src/api/schema.d.ts
```

Dat maakt de frontend compilebaar tegen de echte API — een verkeerde veldnaam wordt een compilefout in plaats van een runtime-verrassing.

## Styling en taal

- Nederlandstalige UI.
- Responsive: de review-UI moet ook op een tablet werken.
- Kleurenblindheidsvriendelijke confidence-codering (niet alleen rood/groen).
- Donkere modus optioneel maar goedkoop via Tailwind.

## Wat er nu bestaat

Niets. [apps/web](../apps/web) bestaat niet. De README noemt Node.js 20+ en pnpm.
