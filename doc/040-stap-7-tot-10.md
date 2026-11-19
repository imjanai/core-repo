# 040 — Stappen 7 tot en met 10: validatie, materiaal, output, review

## Stap 7 — Validatie

**Input:** `Project`. **Output:** `Project.warnings`.

De regelengine loopt over alle regels en levert berichten terug. Zie [047-rules-nen-1010](047-rules-nen-1010.md) voor de huidige regel:

```python
def max_wcd_per_group(p: Project) -> list[str]:
    counts = Counter(s.circuit for s in p.symbols
                     if s.circuit and s.type == "wandcontactdoos")
    return [f"Groep {g} heeft {n} WCD's (controleer belasting)"
            for g, n in counts.items() if n > 8]
```

De engine draait in [packages/rules/rules.py](../packages/rules/rules.py) — het enige deel van de pipeline dat al in code staat.

## Stap 8 — Materiaalengine

**Input:** `Project`. **Output:** materiaallijst.

```
symbool → artikel → hoeveelheid → stuksprijs → regelprijs
```

Bijvoorbeeld:

| type | artikel | aantal | stuksprijs | regelprijs |
|---|---|---|---|---|
| wandcontactdoos | WCD-86-RVS | 24 | € 8,40 | € 201,60 |
| schakelaar | SCH-1V-W | 12 | € 6,10 | € 73,20 |
| lichtpunt | LP-PLAF-W | 15 | € 4,25 | € 63,75 |

Details: [048-materials-engine](048-materials-engine.md).

## Stap 9 — Output

| Formaat | Library | Wat |
|---|---|---|
| Excel | openpyxl | Materiaallijst, per ruimte of per groep |
| PDF | Jinja2 + WeasyPrint | Offerte, rapport met waarschuwingen |
| DXF | ezdxf | Nieuwe of gewijzigde tekening |

De Excel- en PDF-flow is eenvoudig: een sjabloon, de data erin, exporteren.

De DXF-flow is de MCP-kant: de AI bouwt een echte tekening op. Zie [049-drawing-engine](049-drawing-engine.md) en [055-mcp-server](055-mcp-server.md).

## Stap 10 — Review en feedback

De enige stap met een mens.

### Wat de gebruiker ziet

- de tekening met overlappende symbolen (kleur naar confidence),
- een materiaallijst die meebeweegt met de selectie,
- waarschuwingen uit de validatie, per symbool gelinkt,
- een lijst "laagste confidence eerst" — de plekken waar het model twijfelt.

### Wat de gebruiker doet

| Actie | Effect |
|---|---|
| Bevestigen | `source="human"`, confidence=1.0 |
| Type wijzigen | Correctie vastgelegd met oud/nieuw |
| Verplaatsen | x/y gewijzigd |
| Verwijderen | Valse positie gemarkeerd |
| Toevoegen | Gemist punt aangevuld |

### Wat er met correcties gebeurt

```python
class Correction(BaseModel):
    project_id: str
    symbol_id: str
    veld: str              # type | x | y | bestaat
    oud: Any
    nieuw: Any
    reviewer: str
    tijdstip: datetime
```

Die correcties zijn trainingsdata: ze worden, na expliciete toestemming van de klant, toegevoegd aan de dataset en het volgende model. Zie [070-feedbackloop](070-feedbackloop.md) en [084-veiligheid-en-avg](084-veiligheid-en-avg.md).

## Waarom review vóór output in de keten staat

In de README-tabel staat output (9) vóór review (10). In de praktijk wil je de gebruiker **tijdens** het proces laten meekijken: anders beoordeelt hij een materiaallijst zonder te zien welke symbolen eraan ten grondslag liggen. De review-UI toont daarom de tekening én de lijst samen. Zie [019-frontend-architectuur](019-frontend-architectuur.md#3-analysescherm).

## Wat er nu bestaat

Alleen [packages/rules/rules.py](../packages/rules/rules.py). De rest wacht.
