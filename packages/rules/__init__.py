"""
packages/rules — AREI regelengine.

Publieke API
------------
    from packages.rules import validate, list_rules
    from packages.rules import DEFAULT_CONFIG, INDUSTRIAL_CONFIG, COMMERCIAL_CONFIG
    from packages.rules import disable_rule, enable_rule, RulesConfig

    # Residentieel (standaard):
    project = validate(project)

    # Industrieel:
    project = validate(project, config=INDUSTRIAL_CONFIG, scope="industrial")

    # Commercieel (kantoor, winkel):
    project = validate(project, config=COMMERCIAL_CONFIG, scope="commercial")

    # Regels inspecteren (alle, of gefilterd op scope):
    for r in list_rules(scope="residential"):
        print(r["id"], r["article"], r["description"])

Nieuwe AREI-regels toevoegen
-----------------------------
1. Maak `packages/rules/rules/arei_artNN.py` aan.
2. Importeer `@rule` uit `packages.rules.engine`.
3. Decoreer je functie — de engine laadt het bestand automatisch.
4. Zie packages/rules/README.md voor het volledige stappenplan.
"""

from packages.rules.engine import validate, list_rules, disable_rule, enable_rule
from packages.rules.limits import (
    DEFAULT_CONFIG, INDUSTRIAL_CONFIG, COMMERCIAL_CONFIG, RulesConfig,
)

__all__ = [
    "validate",
    "list_rules",
    "disable_rule",
    "enable_rule",
    "DEFAULT_CONFIG",
    "INDUSTRIAL_CONFIG",
    "COMMERCIAL_CONFIG",
    "RulesConfig",
]
