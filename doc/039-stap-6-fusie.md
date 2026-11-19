# 039 — Stap 6: Fusie

## De opgave

Drie sporen leverden waarnemingen:

- vector: `VectorSymbol` met exacte coördinaten en laagnaam,
- detector: `Detection` met bbox en confidence,
- VLM: `RoomProposal`, `Reinterpretatie`, legenda-mapping.

De fusie brengt dat tot **één `Project`**: het enige object waar de rest van het systeem mee werkt.

## De regels, in volgorde

### 1. Als er vectordata is, is die leidend

Principe uit [016-hybride-aanpak](016-hybride-aanpak.md). De detector draait bij vectorbronnen alleen als tegencontrole: een detectie die géén vector-tegenhanger heeft, wordt een waarschuwing ("mogelijk gemist punt"), geen symbool.

### 2. Per waarneming een `Symbol` met `id`, `confidence` en `source`

```python
Symbol(
    id=uuid4(),
    type=..., x=..., y=...,
    confidence=0.93,
    source="detector"
)
```

De `id` wordt hier vastgelegd en nooit meer gewijzigd — de sleutel voor reviews en trainingsdata. Zie [023-symbol-model](023-symbol-model.md).

### 3. Klasse toewijzen via de legenda

Een vector-waarneming met bloknaam "KRING-01" zonder klasse wordt via de legenda-mapping geclassificeerd. Onbekende namen gaan naar het VLM of blijven `UNKNOWN`.

### 4. Ruimtes toewijzen

Punt-in-polygoon-test voor elk symbool tegen elke `Room`. Een symbool buiten alle polygonen krijgt `room_id=None` en een waarschuwing.

### 5. `circuit` invullen

Uit kabelroutes, uit tekst in de buurt ("G3"), of uit het VLM. `None` als onbekend — nooit gokken; `circuit=None` betekent dat de groepsregels dat symbool overslaan, wat beter is dan een verkeerde groep.

### 6. Conflicten vastleggen

Als detector en vector het oneens zijn over de klasse, wint vector maar wordt de detectie genoteerd in `warnings`. Dat is bruikbare feedback voor de volgende detector-versie.

## De volgorde doet ertoe

De fusie is niet commutatief: het bepalen van `circuit` hangt af van `room_id` (een kabel loopt door ruimtes), en `room_id` hangt af van de polygoon die de VLM leverde. De implementatie moet die volgorde respecteren, of expliciet twee passes doen (eerst ruimtes, dan circuits).

## Idempotentie

De fusie moet twee keer draaien hetzelfde `Project` opleveren (op de uuid-na na). Dat maakt hervatten na een crash veilig. Concreet: deterministische sortering van waarnemingen, geen afhankelijkheid van dict-volgorde.

## Wat de fusie níet doet

- **Niet tellen of rekenen.** Dat is de materiaalengine en de regelengine. Zie [040-stap-7-tot-10](040-stap-7-tot-10.md).
- **Niet besluiten wat waar is op basis van confidence.** Confidence wordt doorgegeven, niet weggegooid; de drempels zijn er voor de materiaalengine en de reviewprioriteit.

## Output

```python
class FusieOutput(BaseModel):
    project: Project
```

Vanaf hier is `Project` de enige munt. Zie [021-schema-overview](021-schema-overview.md).

## Wat er nu bestaat

Niets. Alleen het doelmodel (`packages/schema`) staat.
