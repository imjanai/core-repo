# 062 — Het basismodel: Qwen-VL

## Waarom Qwen-VL

De README kiest Qwen-VL als basis voor het eigen vision-language model. De redenen:

- **Sterk in visie-taal-taken**, inclusief document- en tekeninginterpretatie.
- **Meerdere groottes** — van klein (serving-vriendelijk) tot groot (maximumkwaliteit).
- **Open gewichten** — je kunt fijntrainen en self-hosten, wat bij gesloten API's onmogelijk is.
- **Actieve community** en brede ondersteuning in libraries als ms-swift en LLaMA-Factory.

Alternatieven vergeleken: [020-keuzes-en-alternatieven](020-keuzes-en-alternatieven.md).

## De licentie — let goed op

De README waarschuwt expliciet:

> **Modellicentie.** Controleer de licentievoorwaarden van het gekozen Qwen-model voor commercieel gebruik.

Qwen-modellen gebruiken verschillende licenties per grootteserie (bv. Qwen2.5 versus Qwen2.5-VL, en binnen die series verschillende varianten). Voor commercieel gebruik moet je:

1. De licentietekst van het **exacte** modelcontroleren dat je kiest (niet "Qwen in het algemeen").
2. Nagaan of de voorwaarden passen bij een proprietary SaaS-product.
3. De licentie vastleggen in [pyproject.toml](../pyproject.toml)-documentatie of een NOTICE-bestand.

Zie [087-modellicenties](087-modellicenties.md) voor de volledige analyse.

## Welke groottes om te overwegen

| Classe | Voordeel | Wanneer |
|---|---|---|
| Klein (2–4B) | Goedkoop serveren, lage latency | Baseline, als eerste experiment |
| Middel (7–8B) | Sterk balans | Waarschijnlijk de productiemodus |
| Groot (32B+) | Maximaal redeneervermogen | Legenda-interpretatie, moeilijke tekeningen |

Begin klein: het verbetert de meetcyclus. Een slecht proces op een groot model blijft een slecht proces.

## Het domein-verschil

Qwen-VL begrijpt algemene afbeeldingen. Dit project heeft een **specifiekere** taak:

- Nederlandse/Belgische symboolsets,
- legenda's met lokale conventies,
- installatietechnisch jargon.

Daarom fijntrainen: niet omdat het basismodel zwak is, maar omdat het domein smal is. Zie [063-finetuning-lora](063-finetuning-lora.md).

## Wat je nodig hebt voor fine-tuning

- GPU met CUDA (24 GB+ is comfortabel voor QLoRA op 7–8B; meer voor groter),
- `torch`, `transformers`, `peft`, `accelerate`, `qwen-vl-utils` — allemaal al in [pyproject.toml](../pyproject.toml),
- een dataset in JSONL met afbeelding + vraag + antwoord.

## Alternatief: geen fine-tuning

Het is de moeite waard om vóór het trainen te meten hoe ver je komt met het onbewerkte model en een goede prompt. Als dat op de evaluatieset voldoende is, bespaar je een hele traincyclus. Meet het, gok het niet. Zie [068-evaluatieset](068-evaluatieset.md).

## Wat er nu bestaat

Niets. [ml/finetune_vlm.py](../ml/finetune_vlm.py) is leeg.
