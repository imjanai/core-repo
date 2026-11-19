# 046 — De VLM-client

## De rol

De client praat met het geserveerde Qwen-VL-model via vLLM's OpenAI-compatibele API. Hij is verantwoordelijk voor het opbouwen van aanroepen, het parsen van de respons en het afdwingen van structuur.

## De configuratie

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://vllm:8000/v1",   # uit VLLM_BASE_URL
    api_key="geen",                   # vLLM vereist sleutel maar checkt ze niet
)

MODEL = os.environ["VLLM_MODEL"]      # bv. "elektro-vl"
```

De `openai`-client wordt bewust gebruikt: vLLM spreekt hetzelfde protocol, dus dezelfde code werkt tegen een lokale server of tegen een andere provider. Zie [071-model-serving-vllm](071-model-serving-vllm.md).

## Een aanroep

```python
import base64

def beantwoord_vraag(afbeelding_png: bytes, vraag: str) -> str:
    data_uri = "data:image/png;base64," + base64.b64encode(afbeelding_png).decode()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_uri}},
                {"type": "text", "text": vraag},
            ],
        }],
        temperature=0.0,        # determinisme
        max_tokens=1024,
    )
    return response.choices[0].message.content
```

`temperature=0.0` is belangrijk: redeneervragen op tekeningen moeten reproduceerbaar zijn, vooral voor de evaluatieset.

## Afdwingen van JSON

De modeluitvoer is tekst. Voor gestructureerde taken:

```python
def beantwoord_json(afbeelding_png: bytes, vraag: str, schema: type[BaseModel]) -> BaseModel:
    rauw = beantwoord_vraag(afbeelding_png, vraag + "\nAntwoord uitsluitend met geldige JSON.")
    try:
        data = json.loads(_verwijder_codeblok(rauw))
        return schema.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        # een herhaalpoging met de fout in de prompt, dan overslaan
        ...
```

`_verwijder_codeblok` haalt ```json-...``` weg — modellen wrappen JSON vaak in een codeblok.

**Regel:** nooit half-geparste data doorgeven. Bij twijfel: overslaan en loggen. Zie [038-stap-5-vlm-redenering](038-stap-5-vlm-redenering.md) voor de volledige strategie.

## Waar de client wordt gebruikt

| Taak | Input | Output |
|---|---|---|
| Legenda-interpretatie | crop van het legendablok | `LegendaMapping` |
| Ruimtevoorstel | crop van een kamer | `RoomProposal` |
| Herinterpretatie van twijfelgeval | crop van een detectie + context | `Reinterpretatie` |
| Schaal bepalen | crop van schaalaanduiding | `float` |
| Naamgeving onbekende bloknaam | tekst + context | `SymbolType` |

## Begrenzingen

- **Timeout:** maximaal 60 seconden; daarna overslaan.
- **Retries:** één herhaling bij een netwerkfout, met backoff.
- **Caching:** cache op hash van (afbeelding, vraag) — voorkomt dat dezelfde crop twee keer wordt betaald.
- **Batch:** als het model het ondersteunt, meerdere crops in één aanroep.

## Monitoring

Elke aanroep logt naar Langfuse: prompt, tokens, latency, kosten. Dat maakt het mogelijk om te zien welke vragen duur en nuttig zijn, en welke slecht. Zie [080-observability](080-observability.md).

## Wat er nu bestaat

Niets. [packages/vision](../packages/vision) is leeg.
