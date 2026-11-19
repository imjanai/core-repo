# 037 — Stap 4c: Tekst en legenda

## Waarom deze stap de sleutel is

De legenda is het vertaalboek van de tekening: "deze cirkel = wandcontactdoos". Zonder legenda-interpretatie is elke symboolclassificatie een gok. Deze stap maakt tekeningen interpreteerbaar.

## Twee hulpmiddelen

### 1. OCR (PaddleOCR)

Levert tekst met positionering:

```python
class TextSpan(BaseModel):
    tekst: str
    bbox: tuple[float, float, float, float]
    confidence: float
```

Typische vondsten:

- legenda-sleutels ("1 WCD", "L1", "G3"),
- ruimtenamen ("Woonkamer"),
- schaalaanduiding ("schaal 1:100"),
- titelblok-informatie (project, klant, datum),
- groepsnummers bij de verdeler.

### 2. VLM voor interpretatie

OCR geeft tekens; het VLM geeft betekenis. Vragen die je stelt:

- "Welke symbolen worden in deze legenda uitgelegd, en wat betekent elk?"
- "Wat is de schaal van deze tekening?"
- "Noem de ruimtes die u ziet en beschrijf hun locatie."
- "Bij deze verdeler: welke groepsnummers hoort u bij welk symbooltype?"

Zie [046-vision-vlm-client](046-vision-vlm-client.md) voor hoe die aanroepen eruitzien.

## Hoe je een legenda vindt

Een legenda staat typisch:

- rechtsboven of rechtsonder,
- in een kader met een rij symbolen naast tekst,
- met een titel ("Legenda", "Toelichting", "Symbolen").

**Strategie:** gebruik OCR-blokken; zoek naar tekst die lijkt op een titel; crop dat gebied; stuur de crop naar het VLM met de vraag om de mapping terug te geven als JSON. De crop is belangrijk: een hele tekening naar het VLM sturen verspilt tokens en verlaagt de nauwkeurigheid.

## Het resultaat: een legenda-mapping

```python
class LegendaMapping(BaseModel):
    entries: list[LegendaEntry]

class LegendaEntry(BaseModel):
    type: SymbolType
    beschrijving: str
    bbox: tuple[float, float, float, float]   # op de tekening
```

Deze mapping voedt stap 6 (fusie): waarnemingen met een vorm maar zonder klasse worden aan de hand van de legenda geclassificeerd. En ze voedt de vector-parser: een bloknaam zonder betekenis kan via de legenda alsnog een type krijgen.

## Waar deze stap faalt

| Faalgeval | Signaal | Mitigatie |
|---|---|---|
| Geen legenda aanwezig | Geen titelblok-gebied gevonden | Val terug op generieke naamgevingstabel |
| Handgeschreven legenda | OCR-confidence laag | VLM op de crop, niet op de OCR-tekst |
| Legenda op meerdere pagina's | Splitsen per pagina | Mergen van mappings |
| Legenda gebruikt andere symbolen dan het model | Conflict bij fusie | Waarschuwing + review |

## Kwaliteit meten

De legenda-stap heeft een eigen meetpunt: **percentage correct geïnterpreteerde legenda-entrie's** op de evaluatieset. Dat cijfer is los van mAP en zegt of de bottleneck bij detectie of bij interpretatie ligt. Zie [069-metrics](069-metrics.md).

## Wat er nu bestaat

Niets. [packages/vision](../packages/vision) en [ml/finetune_vlm.py](../ml/finetune_vlm.py) (leeg) wachten op invulling.
