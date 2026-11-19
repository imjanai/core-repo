# 070 — De feedbackloop

## Het idee

> Correcties uit de review-UI (`POST /corrections`) komen als nieuwe voorbeelden in de dataset. Hertrainen gebeurt periodiek via een geautomatiseerde workflow, met automatische regressietest voor promotie.

Dit is waar het platform beter wordt met gebruik — en het duurzame voordeel van de architectuur.

## De keten

```
AI-stelvoorstel
      ↓
vakman corrigeert in de review-UI
      ↓
Correction-objecten → database
      ↓
(aggregatie + anonymisering + toestemming)
      ↓
dataset v2 → hertraining → evaluatieset → promotiegate
      ↓
beter model → betere voorstellen → minder correcties
```

## Stap voor stap

### 1. Correcties vastleggen

```python
class Correction(BaseModel):
    project_id: str
    symbol_id: str
    veld: str                # type | x | y | bestaat
    oud: Any
    nieuw: Any
    reviewer: str
    tijdstip: datetime
```

### 2. Toestemming controleren

Klantdata wordt **alleen met expliciete toestemming** voor training gebruikt. Zonder toestemming: de correctie verbetert het project maar gaat niet naar de dataset. Zie [084-veiligheid-en-avg](084-veiligheid-en-avg.md).

### 3. Omzetten naar trainingsvoorbeelden

| Correctie | Nieuw voorbeeld |
|---|---|
| Type gewijzigd | Afbeeldingscrop + "welk type?" → nieuw type |
| Verwijderd | Crop + label "geen symbool" (negatief voorbeeld) |
| Toegevoegd | Crop + nieuw type |
| Verplaatst | Crop met gecorrigeerde box (detector) |

### 4. Aggregeren en anonimiseren

Per project een export met geanonimiseerde titelblokken. Zie [066-datasetstructuur](066-datasetstructuur.md).

### 5. Hertrainen

Periodiek — de README noemt maandelijks in Fase 2. Automatisch, maar met een expliciete promotiegate.

### 6. Promoveren

Evaluatieset draaien; bij regressie niet publiceren. Zie [083-cicd](083-cicd.md).

## De drie vallen

### 1. Bias door alleen correcties te gebruiken

Correcties zijn scheef: gebruikers corrigeren wat opvalt, niet wat stilletjes klopt. Los op: meng correcties met handmatig gelabelde data en houd de gouden set onaangeroerd.

### 2. Kwaliteit van de correctie

Een verkeerde correctie is slechtere data dan geen data. Mitigaties:

- review door een tweede persoon op steekproef,
- alleen correcties van gebruikers met voldoende ervaring in het systeem,
- conflicterende correcties op hetzelfde symbool signaleren.

### 3. Te vroeg hertrainen

Te weinig correcties → ruis in de training → geen verbetering of verslechtering. Stel een minimum in (bv. minimaal N nieuwe projecten of M correcties) vóór een hertraining wordt gestart.

## Het meetpunt van de loop

**% tekeningen zonder correctie** per maand. Als dat stijgt, werkt de loop. Als het vlak blijft, is er iets mis: te weinig data, te slechte labels, of een model dat niet leert. Zie [069-metrics](069-metrics.md).

## Wat er nu bestaat

Niets. Er is geen review-UI, geen `POST /corrections` en geen dataset.
