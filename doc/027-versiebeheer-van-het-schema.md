# 027 — Versiebeheer van het schema

## Het probleem

Op een gegeven moment staat er een `Project` in de database die gisteren is opgeslagen. Vandaag wijzig je `Symbol` met een nieuw veld. Wat gebeurt er als je die oude vermelding terugleest?

## De regel

> Het schema mag alleen toevoegen met een default; bestaande velden verwijderen of hernoemen gebeurt alleen met een expliciete migratie en een versie-stijging.

## Veilige versus onveilige wijzigingen

| Wijziging | Veilig? | Voorbeeld |
|---|---|---|
| Veld toevoegen met default | ✅ | `rotation: float = 0.0` |
| Veld toevoegen verplicht zonder default | ❌ | `rotation: float` |
| Enum-waarde toevoegen | ✅ meestal | `MOTION = "bewegingsschakelaar"` |
| Enum-waarde verwijderen | ❌ | Bestaande data wordt ongeldig |
| Veldtype wijzigen | ❌ | `confidence: float` → `str` |
| Default wijzigen | ⚠️ | Verandert gedrag voor oude data |
| Veld verwijderen | ❌ | Verwijst nog uit opgeslagen JSON |

## De strategie

### 1. Voeg `schema_version` toe aan `Project`

```python
class Project(BaseModel):
    schema_version: int = 1
    ...
```

### 2. Migratiefuncties per versie

```python
MIGRATIONS = {
    1: migrate_1_to_2,   # bv. source: str → SymbolSource-enum
}

def load(raw: dict) -> Project:
    v = raw.get("schema_version", 1)
    while v < CURRENT_VERSION:
        raw = MIGRATIONS[v](raw)
        v += 1
    return Project.model_validate(raw)
```

### 3. Schrijf nooit weg voordat het gelezen is

De API leest een Project, bewerkt het en schrijft het terug. Als er twee versies tegelijk in omloop zijn (oud model in de worker, nieuw model in de API), kan een nieuw veld verdwijnen door een oude serialize-pass. Voorkom dat door:

- schema-wijzigingen en deploy samen te laten vallen,
- additive-only wijzigingen binnen één release.

## Wat er nu mist

- Er is geen `schema_version`.
- Er is geen `model_config = ConfigDict(extra="forbid")` — extra velden worden nu stilzwijgend weggegooid door Pydantic, wat data kan verliezen zonder waarschuwing. Overweeg `extra="ignore"` expliciet te documenteren of `extra="forbid"` te gebruiken om onbekende data te signaleren.

## Wanneer dit ertoe doet

- Fase 1: nog geen probleem — er staat niets in productie.
- Fase 2: wél — het eerste model dat op correctiedata getraind wordt, veronderstelt stabiele id's en velden.
- Fase 5 (integraties): partners hebben het schema gekopieerd; elke brekende wijziging is dan een coördinatieprobleem.

Regel voor nu: **maak alleen toevoegingen met defaults**, en leg `schema_version` vast vóór de eerste pilot.
