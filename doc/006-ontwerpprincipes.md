# 006 — De zes ontwerpprincipes

De README noemt zes principes. Ze zijn niet decoratief: elk principes sluit een concrete mislukkingsscenario af.

---

## 1. Hybride in plaats van alleen een model

**Principe:** Vectortekeningen worden exact uitgelezen; het VLM is er voor raster en voor interpretatie.

**Waarom:** Een DXF bevat exacte coördinaten. Een model laten "raden" naar die coördinaten voegt ruis toe aan data die al perfect is. Andersom kan geen enkele parser afleiden dat een legenda-cirkel "wandcontactdoos" betekent — dat is interpretatie.

**Gevolg in de architectuur:** drie parallelle analysepaden die later samenkomen ([039-stap-6-fusie](039-stap-6-fusie.md)).

**Mislezen als:** "we gebruiken AI waar het kan" — het is precies omgekeerd: *we gebruiken AI alleen waar het moet*.

---

## 2. Eén bron van waarheid

**Principe:** Alle onderdelen praten met hetzelfde Pydantic-projectmodel (`packages/schema`).

**Waarom:** Zonder gedeeld model krijgt de API zijn eigen idee van wat een "symbool" is, de worker een ander, en de frontend een derde. Elke wijziging wordt dan een coördinatieprobleem.

**Gevolg in de code:** `Project`, `Symbol`, `Room` zijn de enige munt waarin informatie wordt uitgewisseld. Elke Celery-task heeft getypte input en output ([017-taken-architectuur](017-taken-architectuur.md)).

**Regel voor bijdragers:** voeg je een veld toe, voeg je het toe in `packages/schema` — niet lokaal in één app.

---

## 3. Tellen en rekenen doet code, niet het model

**Principe:** Aantallen, optellingen, prijzen en normgrenzen komen uit Python, nooit uit een taalmodel.

**Waarom:** LLM's tellen onbetrouwbaar, en een offerte met een verkeerd aantal is direct financiële schade. Deterministische code is testbaar, reproduceerbaar en uitlegbaar richting klant.

**Gevolg:** de materiaalengine en regelengine zijn pure functies over `Project` ([047](047-rules-nen-1010.md), [048](048-materials-engine.md)).

**Randvoorbeeld:** als het model zegt "ik zie 12 wcd's", is dat een *detectie* (met confidence en source), geen *telling*. De telling gebeurt na fusie, over de gefuseerde lijst.

---

## 4. Mens in de loop

**Principe:** De AI doet voorstellen, de vakman keurt goed.

**Waarom:** Aansprakelijkheid en kwaliteit. Zie [085-aansprakelijkheid](085-aansprakelijkheid.md). Ook pragmatisch: een systeem dat 90% voorstelt en 10% laat bevestigen is waardevol; een systeem dat 100% zelfstandig beslist is onbetrouwbaar én juridisch riskant.

**Gevolg:** de review-UI is geen nice-to-have maar een verplichte schakel in de pipeline (stap 10, [040](040-stap-7-tot-10.md)).

---

## 5. Elke correctie is trainingsdata

**Principe:** Correcties uit de review-UI komen als nieuwe voorbeelden in de dataset; het systeem wordt met gebruik beter.

**Waarom:** Dit is het duurzame voordeel. Een beter basismodel kan iedereen nabootsen; een groeiende, gelabelde dataset van echte Nederlandse/Belgische installatietekeningen niet.

**Gevolg:** `POST /corrections` → dataset → periodieke hertraining → regressietest ([070-feedbackloop](070-feedbackloop.md)).

**Constrainerend:** klantdata mag alleen met expliciete toestemming voor training worden gebruikt (zie [084-veiligheid-en-avg](084-veiligheid-en-avg.md)).

---

## 6. Meten voor je verbetert

**Principe:** Geen modelversie live zonder regressietest op de evaluatieset.

**Waarom:** Fine-tuning is niet-monotoon beter. Een model dat op geheugen leert kan op de evaluatieset verslechteren terwijl de loss daalt.

**Gevolg:** de evaluatieset is heilig en nooit trainingsdata ([068-evaluatieset](068-evaluatieset.md)); promoveren gebeurt via een gate in CI ([083-cicd](083-cicd.md)).

---

## Samenhang

De zes principes ondersteunen elkaar:

```
hybride (1)  ─┬─► levert rijke waarnemingen
              └─► vereist één model (2) om te fuseren
                     │
                     ├─► code rekent (3) op dat model
                     ├─► mens beoordeelt (4) dat model
                     └─► correcties (5) verbeteren waarneming (1)
                              │
                              └─► meten (6) bewijst verbetering
```

Eén principes schrappen breekt de keten. Bij een ontwerpgesprek is dit de eerste toets.
