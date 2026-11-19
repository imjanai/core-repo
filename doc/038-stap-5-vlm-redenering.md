# 038 — Stap 5: VLM-redenering

## Wat deze stap uniek maakt

Dit is de enige stap waar het model **redeneert** in plaats van waarnemen. De vorige stappen leverden losse observaties; deze stelt context samen en beantwoordt vragen die geen enkele parser kan beantwoorden.

## De drie soorten taken

### 1. Ruimtes afleiden

De vector-parser kan wandcontouren leveren; het VLM kan afleiden wat een ruimte *is*:

> "Deze ruimte met een douche, wastafel en tegels is de badkamer."

Output: `RoomProposal { polygon, naam, zekerheid }`.

**Waarom het VLM hier goed in is:** het herkent inrichting en context — iets dat een parser niet ziet en een detector niet kan.

### 2. Onzekere detecties herinterpreteren

Detecties met lage confidence of conflicterende vormen gaan naar het VLM:

> "Ik zie op deze plek een klein rond object met een kruis. Is dit een lichtpunt of een rookmelder? Kijk naar de context: het plafond in de keuken."

Output: `Reinterpretatie { detection_id, voorgesteld_type, reden, confidence }`.

**De discipline:** het VLM mag een suggestie doen, geen besluit nemen. Het verschil zie je in `Symbol.source` — `vlm` weegt minder zwaar dan `vector` bij fusie. Zie [039-stap-6-fusie](039-stap-6-fusie.md).

### 3. Legenda en kabelroutes

- De legenda-interpretatie (zie [037](037-stap-4c-tekst-en-legenda.md)).
- Het volgen van kabellijnen tussen verdeler en groepen, om `Symbol.circuit` te vullen — cruciaal voor de regelengine.

## De prompt-structuur

```python
messages = [{
    "role": "user",
    "content": [
        {"type": "image", "image": cropped_png},
        {"type": "text", "text": PROMPT_MET_CONCRETE_VRAAG}
    ]
}]
```

Belangrijk:

- **Crop, niet de hele tekening.** Minder tokens, betere nauwkeurigheid.
- **Vraag om JSON.** Niet om proza. Bijv.: "Geef een JSON-lijst van ruimtes met polygon-coördinaten in pixels en een naam."
- **Eén vraag per aanroep.** Gecombineerde vragen leveren vermengde, onbetrouwbare output op.
- **Geef context mee.** De legenda-crop erbij sturen als het model een symbool moet classificeren verhoogt de nauwkeurigheid aanzienlijk.

## Structuur afdwingen

De output van een VLM is tekst, geen garantie. Daarom:

1. Vraag expliciet om JSON.
2. Parse met `json.loads` in een try-except.
3. Valideer met een Pydantic-model.
4. Bij mislukking: één herhaalpoging met de foutmelding in de prompt.
5. Bij opnieuw mislukking: de waarneming overslaan en loggen — nooit half-geparste data doorgeven.

Zie [028-validatie-in-het-schema](028-validatie-in-het-schema.md) voor waarom die validatie niet optioneel is.

## Kosten en begrenzing

Elke VLM-aanroep kost tokens en GPU-tijd. Begrenzen:

- maximaal N crops per tekening (alleen bij twijfel),
- caching op inhoud-hash (dezelfde crop → hetzelfde antwoord),
- batch-verwerking waar het model dat ondersteunt.

Zie [097-prestaties-en-schaal](097-prestaties-en-schaal.md).

## Wat er nu bestaat

Niets. [packages/vision](../packages/vision) is leeg; [ml/finetune_vlm.py](../ml/finetune_vlm.py) is een leeg bestand. De fine-tuning zelf staat uitgelegd in [063-finetuning-lora](063-finetuning-lora.md).
