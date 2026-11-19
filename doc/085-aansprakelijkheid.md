# 085 — Aansprakelijkheid: de vakman beslist

## De kern uit de README

> **De AI is een assistent, geen eindverantwoordelijke.** Ontwerp, dimensionering en oplevering blijven de verantwoordelijkheid van de bevoegde installateur. Dit wordt vastgelegd in de gebruiksvoorwaarden.

## Waarom dit een architectuurkeuze is, geen juridische bijschrift

De hele ontwerpfilosofie ondersteunt dit:

1. **Tellen en rekenen doet code** — reproduceerbaar en controleerbaar.
2. **Mens in de loop** — de review-UI is een verplichte schakel.
3. **`source` en `confidence`** — elke waarneming draagt hoe zeker hij is en waar hij vandaan komt.
4. **Regels uit de norm** — grenswaarden worden door een domeinexpert beheerd, niet door een model.

Zie [006-ontwerpprincipes](006-ontwerpprincipes.md).

## Concreet in het product

| Aspect | Implementatie |
|---|---|
| Review verplicht | Geen materiaallijst "definitief" zonder bevestiging |
| Onzichtbaarheid voorkomen | Twijfel-lijst toont lage confidence expliciet |
| Herleidbaarheid | Elke symbool heeft `source`; elke analyse heeft een modelversie-log |
| Waarschuwingen | Regels waarschuwen, blokkeren niet — de vakman beslist |
| Export | Watermerk of notitie "AI-voorstel, gecontroleerd door [naam]" |

## In de gebruiksvoorwaarden

Vastleggen:

1. Het platform is een **rekenkundig en interpretatief hulpmiddel**.
2. De gebruiker is **verplicht het resultaat te controleren** vóór uitvoering.
3. De **bevoegdheid** tot ontwerp en oplevering ligt bij de gebruiker.
4. De **norm** (NEN 1010) is leidend, niet de software.
5. Aansprakelijkheid voor schade uit ongecontroleerd gebruik ligt bij de gebruiker — met een redelijke inspanningsverplichting van onze kant (kwaliteit, veiligheid, updates).

Laat die voorwaarden beoordelen door een jurist met kennis van de bouw en de elektrotechniek; dit document is technisch, geen juridisch advies.

## De spanning die je moet balanceren

- **Te voorzichtig** ("alleen een suggestie, controleer alles") → waardeverlies, de gebruiker doet alsnog alles zelf.
- **Te stellig** ("de offerte klopt") → aansprakelijkheid en wantrouwen als het misgaat.

De juiste toon: **betrouwbaar waar het exact is, expliciet onzeker waar het interpretatief is.** Het `confidence`- en `source`-veld maakt dat technisch mogelijk; de UI moet het zichtbaar maken.

## Wat er nu bestaat

Niets in code. Het beginsel staat alleen in de README.
