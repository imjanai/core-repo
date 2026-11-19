# 063 — Fine-tuning met LoRA/QLoRA

## Het idee

In plaats van het hele model bij te trainen (duur, geheugenvretend, risico op forgotten knowledge), train je kleine **trainbare matrices** met lage rang naast de bevroren gewichten.

```
origineel:  W  (bevroren)
getraind:   W + B·A   waar A en B klein zijn (rang r)
```

- **LoRA**: trainbare matrices in float16/bf16.
- **QLoRA**: de basis is 4-bits genantiseerd, de matrices in bf16 — nog minder geheugen.

## Waarom dit de juiste keuze is

| | Volledige fine-tune | LoRA/QLoRA |
|---|---|---|
| Geheugen | Zeer hoog | 24 GB haalbaar |
| Kosten per iteratie | Duur | Goedkoop |
| Risico op forgetting | Hoog | Laag |
| Itereren | Langzaam | Snel |
| Kwaliteit | Bovenste grens | In de praktijk vergelijkbaar voor smalle domeinen |

Voor een domein met vijf klassen en een herkenbare visuele stijl is LoRA meestal ruim voldoende.

## Gereedschap: ms-swift of LLaMA-Factory

De README noemt beide. Beide zijn matuur:

| | ms-swift | LLaMA-Factory |
|---|---|---|
| Ondersteuning Qwen-VL | Sterk | Sterk |
| Interface | CLI | Web-UI + CLI |
| Configuratie | YAML | YAML |
| Onderhoud | Actief | Actief |

**Advies:** kies er één en leg de keuze vast — wisselen kost meer dan het oplevert. Vooraf testen op een klein experiment is verstandiger dan een lange discussie.

## Het datasetformaat

JSONL met per voorbeeld: afbeelding, vraag, antwoord.

```json
{"images": ["pagina_012.png"],
 "conversations": [
   {"from": "human", "value": "<image>Welke symbolen betekent deze legenda? Geef JSON."},
   {"from": "gpt", "value": "[{\"type\": \"wandcontactdoos\", \"symbool\": \"cirkel met kruis\"}]"}
 ]}
```

Belangrijk:

- **Afbeeldingen in een stabiel pad** dat ook bij serving bestaat.
- **Antwoorden in het formaat dat de pipeline verwacht** — JSON, geen proza.
- **Mix van taken** per epoch: legenda, ruimtes, herinterpretatie, schaal.
- **Geen evaluatieset.** Zie [068-evaluatieset](068-evaluatieset.md).

## Een typische configuratie

```yaml
model: Qwen/Qwen2.5-VL-7B-Instruct
method: lora
lora_rank: 16
lora_alpha: 32
learning_rate: 1.0e-4
epochs: 3
batch_size: 1
gradient_accumulation: 8
bf16: true
```

Begin klein, verhoog pas bij aanhoudende underfitting. Vaak is meer en betere data effectiever dan een groter model.

## De valkuilen

| Valkuil | Symptoom | Oplossing |
|---|---|---|
| Overfitting op weinig data | Train-loss daalt, evaluatieset verslechtert | Meer data, minder epochs, hogere rank |
| Data leakage | Evaluatieset scoort verdacht hoog | Controleer splitsing; zie [068](068-evaluatieset.md) |
| Antwoorden in vrije tekst | Pipeline faalt bij parsing | Vraag expliciet om JSON; valideer tijdens dataverzameling |
| Ongebalanceerde klassen | Model voorspelt bijna altijd WCD | Oversampling of gewichten |
| Niet-reproduceerbare runs | Resultaten verschillen per keer | Seed vastleggen, config meearchiveren |

## Wat er nu bestaat

[ml/finetune_vlm.py](../ml/finetune_vlm.py) is een leeg bestand — klaar voor deze implementatie.
