# 067 — Labeling

## De bottleneck

Voor een domein met vijf klassen is het model eenvoudig. **Data verzamelen en labelen is het echte werk.**

Indicatie: het labelen van één installatietekening kost 20–60 minuten, afhankelijk van het aantal symbolen en de kwaliteit van de tekening. Voor 100 tekeningen: 33–100 uur.

## De tools

| Tool | Sterk in |
|---|---|
| **CVAT** | Objectdetectie, polygonen, video; export naar YOLO/COCO |
| **Label Studio** | Veelzijdig, LLM-assisted labeling, makkelijk uitbreidbaar |

Beide staan in de README. Kies er één bij de eerste labelronde en leg de keuze vast.

## Wat er gelabeld wordt

### Voor de detector

Bounding boxes per symbool, klasse uit `SymbolType`:

```json
{"bbox": [x, y, w, h], "label": "wandcontactdoos"}
```

### Voor de VLM

Vraag/antwoord-paren:

- "Wat betekent deze legenda?" → JSON-mapping
- "Noem de ruimtes op deze tekening" → JSON met namen en polygonen
- "Bij welke groep hoort deze WCD?" → "G3"

Deze paren komen deels uit de review-correcties (stap 10) — zie [070-feedbackloop](070-feedbackloop.md).

### Voor de gouden set

Voor ±50 tekeningen is een **volledig handmatig gecontroleerde** grondwaarde nodig: elk symbool, elk type, elke ruimte. Dat is duur maar onmisbaar: zonder grondwaarde geen mAP en geen materiaalfout-meting.

## Efficiëntietips

1. **Model-in-the-loop.** Laat de detector een voorstel doen; de labeler corrigeert. Dat is twee tot vijf keer sneller dan handmatig — mits het model niet zo slecht is dat vertrouwen in de voorstellen verdwijnt.
2. **Label per tekening, niet per symbooltype.** Minder contextwissels.
3. **Leg een stijlgids vast.** Wat is een lichtpunt versus een bewegingsschakelaar op een afwijkende tekening? Zonder afspraken labelen twee anotatoren hetzelfde anders.
4. **Meet inter-annotator agreement.** Laat een steekproef door twee mensen labelen; de overlap zegt iets over de haalbare plafonduur van het model.

## De stijlgids (voorbeeldvragen)

- Wat doe je met een symbool half over een muur? → labelen, centrum bepalen.
- Wat doe je met een onleesbaar symbool? → labelen als `onbekend`, niet overslaan.
- Wat doe je met symbolen op een legenda? → **niet labelen** — een legenda is geen installatiepunt. Dit is een klassieke bron van foutpositieven.

Die laatste regel is belangrijk: als de detector de legendasymbolen als echte symbolen leert, telt de pipeline ze mee in de materiaallijst.

## Exporteren

Na labelen exporteren naar het juiste formaat:

- detector → YOLO (of COCO, geconverteerd),
- VLM → JSONL,
- gouden set → JSON met alle grondwaarden.

Zie [066-datasetstructuur](066-datasetstructuur.md).

## Wat er nu bestaat

Niets. Er is geen dataset en geen labeling-configuratie.
