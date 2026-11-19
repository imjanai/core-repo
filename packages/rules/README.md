# packages/rules — AREI regelengine

## Structuur

```
packages/rules/
├── __init__.py          publieke API
├── engine.py            registry, @rule decorator, validate()
├── limits.py            drempelwaarden (RulesConfig dataclass)
├── rules/               één .py per AREI-artikel
│   ├── __init__.py
│   ├── arei_art4.py     Art. 4 — groepsleidingen & belasting
│   ├── arei_art6.py     Art. 6 — aardlekbeveiliging
│   ├── arei_art7.py     Art. 7 / NBN S21-208 — brandbeveiliging
│   └── arei_project.py  Installatieniveau-volledigheid
└── README.md            dit bestand
```

## Nieuwe AREI-regel toevoegen

1. Maak `packages/rules/rules/arei_artNN.py` aan (NN = artikelnummer).
2. Decoreer je functie met `@rule(...)`:

```python
from packages.rules.engine import rule
from packages.rules.limits import RulesConfig
from packages.schema import Project, ValidationWarning

@rule(
    id="AREI-X.Y.Z-MNEMONIC",   # unieke ID, altijd AREI-artikel-omschrijving
    description="Korte omschrijving voor de review-UI",
    article="AREI Art. X.Y.Z",  # exact artikelnummer
    source="AREI 2023",         # editie + jaar
    applies_to={"residential"},  # of {"industrial"}, {"all"}, ...
    severity="warning",          # "info" | "warning" | "error"
)
def mijn_nieuwe_regel(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    Exacte AREI-tekst als docstring, incl. pagina/paragraafnummer.
    """
    ...
    return [ValidationWarning(code="AREI-X.Y.Z-MNEMONIC", severity="warning",
                              message="...", symbol_ids=[...])]
```

3. De engine laadt het bestand automatisch — geen registratie nodig.
4. Schrijf een test in `tests/rules/test_engine.py`.

## Drempelwaarden aanpassen

Alle grenswaarden staan in `limits.py`, gegroepeerd per onderwerp.
Pas ze aan zonder de regellogica te wijzigen:

```python
from dataclasses import replace
from packages.rules.limits import DEFAULT_CONFIG, CircuitLimits

strikt = replace(DEFAULT_CONFIG, circuit=CircuitLimits(max_wcd=6))
project = validate(project, config=strikt)
```

## Scopes

| Scope          | Gebruik                          |
|----------------|----------------------------------|
| `residential`  | Woningen, appartementen          |
| `commercial`   | Kantoren, winkels, horeca        |
| `industrial`   | Industriële installaties         |
| `all`          | Altijd, ongeacht installatietyp  |

## Bronnen

| Bron             | Editie  | Onderwerp                          |
|------------------|---------|------------------------------------|
| AREI             | 2023    | Algemeen Reglement Elektrische Installatiesaties (België) |
| NBN S21-208      | 2013    | Rookmelders in woningen (België)   |
| NEN-EN 1838      | 2013    | Noodverlichting                    |
| NEN 1010         | 2020    | Laagspanningsinstallaties (NL ref) |
