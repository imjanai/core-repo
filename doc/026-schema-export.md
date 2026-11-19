# 026 — `schema.py` en de openstaande TODO

## De huidige inhoud

```python
# packages/schema/schema.py
# TODO: Exporting all sub schemas.
```

Eén regel commentaar. Dat is de hele `schema.py`.

## Wat deze file moet worden

De **publieke ingang** van het schema-pakket: de plek waar alles samenkomt zodat de rest van het systeem één ding hoeft te importeren.

```python
# packages/schema/__init__.py  (of schema.py, afhankelijk van de keuze)
from packages.schema.symbol import Symbol, SymbolType, SymbolSource
from packages.schema.room import Room
from packages.schema.project import Project
from packages.schema.warning import Warning

__all__ = ["Symbol", "SymbolType", "SymbolSource", "Room", "Project", "Warning"]
```

## Het concrete probleem dat het oplost

[packages/rules/rules.py](../packages/rules/rules.py) begint met:

```python
from schema import Project
```

Die import werkt nu niet:

1. er is geen `schema`-pakket dat als zodanig geïnstalleerd is,
2. er is geen `__init__.py` die `Project` exporteert,
3. de modellen importeren elkaar weliswaar correct (`from packages.schema.room import Room`), maar de regels laten zich niet importeren zonder PYTHONPATH-trucs.

**Zonder deze TODO afgerond is `packages/rules` niet testbaar.** Zie [030-schema-verschillen-met-readme](030-schema-verschillen-met-readme.md) voor de volledige analyse.

## De keuze: `__init__.py` of `schema.py`?

| Optie | Voor | Tegen |
|---|---|---|
| **`packages/schema/__init__.py`** | Python-standaard; `from packages.schema import Project` | Verward als er ook een `schema.py` is |
| **`packages/schema/schema.py` als aggregator** | Bestaat al (als placeholder) | Dubbele betekenis met de mapnaam |
| **Beide: `__init__.py` exporteert, `schema.py` blijft** | Zachte migratie | Onderhoud van twee entry-points |

**Aanbeveling:** gebruik `__init__.py` als enige entry-point en verwijder `schema.py`. De mapnaam `schema` is dan de namespace; `import schema` van buitenaf is ongewenst omdat het te generiek is (bots met andere libraries).

## Aanbevolen werkende situatie

```toml
# pyproject.toml (per pakket, na workspace-migratie)
[project]
name = "imjan-schema"
```

```python
# packages/schema/__init__.py
from packages.schema.symbol import Symbol, SymbolType
from packages.schema.room import Room
from packages.schema.project import Project

__all__ = ["Symbol", "SymbolType", "Room", "Project"]
```

```python
# packages/rules/rules.py
from imjan_schema import Project      # in plaats van "from schema import Project"
```

Of, als de repo-lay-out als PYTHONPATH-waarden blijft:

```python
from packages.schema import Project
```

Kies één van de twee en documenteer het. Zie [013-monorepo-workspace](013-monorepo-workspace.md).

## Hoe je de TODO afsluit

1. Bepaal de naamgeving (workspace-pakket versus PYTHONPATH).
2. Schrijf `packages/schema/__init__.py` met expliciete exports.
3. Pas [packages/rules/rules.py](../packages/rules/rules.py) aan naar de nieuwe import.
4. Voeg `packages/rules/__init__.py` toe.
5. Schrijf een test die `from packages.rules import validate` uitvoert — dat bewijst dat de keten werkt.
6. Verwijder `schema.py` of vul hem met een deprecation-bericht.
7. Pas `uv run mypy .` toe en controleer dat het schema-pakket geen cyclische importen heeft.

## Waarom dit prioriteit heeft

Elke minuut dat het schema niet correct geëxporteerd wordt, vertraagt elke ontwikkelaar die aan de regels, materialen of API werkt. Dit is een klein stukje werk met een grote hefboom.
