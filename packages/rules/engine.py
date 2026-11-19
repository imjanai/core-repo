"""
packages/rules/engine.py — regelregistry en uitvoeringsmotor.

Regelmodules (packages/rules/rules/*.py) registreren hun functies via de
`@rule(...)` decorator.  De engine importeert alle modules bij opstart en
voert ze uit via validate().

Regelauteurs schrijven ALLEEN een module in rules/; de engine hoeft niet
gewijzigd te worden.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from dataclasses import dataclass, field
from typing import Callable

from packages.schema import Project, ValidationWarning
from packages.rules.limits import DEFAULT_CONFIG, RulesConfig

logger = logging.getLogger(__name__)

RuleFunc = Callable[[Project, RulesConfig], list[ValidationWarning]]

VALID_SCOPES = {"residential", "industrial", "commercial", "all"}


# ---------------------------------------------------------------------------
# Registratie-dataclass
# ---------------------------------------------------------------------------


@dataclass
class RuleRegistration:
    id: str
    description: str
    fn: RuleFunc
    article: str          # bv. "AREI Art. 4.4.2"
    source: str           # bv. "AREI 2023" of "NBN S21-208:2013"
    applies_to: set[str]  # {"residential"} | {"all"} | {"residential","industrial"}
    severity: str = "warning"   # "info" | "warning" | "error"
    enabled: bool = True


_REGISTRY: list[RuleRegistration] = []


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def rule(
    *,
    id: str,
    description: str,
    article: str,
    source: str,
    applies_to: set[str] | None = None,
    severity: str = "warning",
    enabled: bool = True,
) -> Callable[[RuleFunc], RuleFunc]:
    """
    Registreer een functie als AREI-regel.

    Gebruik:
        @rule(
            id="AREI-4.4.2-WCD",
            description="Max WCD's per groepsleiding",
            article="AREI Art. 4.4.2",
            source="AREI 2023",
            applies_to={"residential", "industrial"},
        )
        def check_wcd(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
            ...
    """
    scopes = applies_to or {"all"}
    unknown = scopes - VALID_SCOPES
    if unknown:
        raise ValueError(f"Onbekende scope(s) in regel '{id}': {unknown}")

    def decorator(fn: RuleFunc) -> RuleFunc:
        _REGISTRY.append(RuleRegistration(
            id=id,
            description=description,
            fn=fn,
            article=article,
            source=source,
            applies_to=scopes,
            severity=severity,
            enabled=enabled,
        ))
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Publieke interface
# ---------------------------------------------------------------------------


def validate(
    project: Project,
    config: RulesConfig = DEFAULT_CONFIG,
    scope: str = "residential",
) -> Project:
    """
    Voert alle actieve, scope-toepasselijke regels uit op het project.
    Schrijft het resultaat naar project.warnings en geeft het Project terug.

    Parameters
    ----------
    project:  het te valideren project
    config:   drempelwaarden (DEFAULT_CONFIG voor woningen)
    scope:    "residential" | "industrial" | "commercial"
              Regels met applies_to={"all"} lopen altijd mee.
    """
    _ensure_rules_loaded()

    active = [
        r for r in _REGISTRY
        if r.enabled and (scope in r.applies_to or "all" in r.applies_to)
    ]

    all_warnings: list[ValidationWarning] = []
    for reg in active:
        try:
            result = reg.fn(project, config)
            all_warnings.extend(result)
            if result:
                logger.debug(
                    "Regel %s (%s): %d waarschuwing(en)",
                    reg.id, reg.article, len(result),
                )
        except Exception:
            logger.exception("Regel %s mislukt — wordt overgeslagen", reg.id)

    project.warnings = all_warnings
    logger.info(
        "validate: %d waarschuwing(en) voor project %s (scope=%s)",
        len(all_warnings), project.id, scope,
    )
    return project


def list_rules(scope: str | None = None) -> list[dict]:
    """
    Overzicht van alle geregistreerde regels, optioneel gefilterd op scope.
    Handig voor de review-UI en de documentatiegenerator.
    """
    _ensure_rules_loaded()
    result = []
    for r in _REGISTRY:
        if scope and scope not in r.applies_to and "all" not in r.applies_to:
            continue
        result.append({
            "id": r.id,
            "description": r.description,
            "article": r.article,
            "source": r.source,
            "applies_to": sorted(r.applies_to),
            "severity": r.severity,
            "enabled": r.enabled,
        })
    return result


def disable_rule(rule_id: str) -> None:
    """Schakel een regel uit (bijv. tijdens tests of voor uitzonderingen)."""
    for r in _REGISTRY:
        if r.id == rule_id:
            r.enabled = False
            return
    raise KeyError(f"Regel '{rule_id}' niet gevonden in de registry.")


def enable_rule(rule_id: str) -> None:
    """Schakel een eerder uitgeschakelde regel opnieuw in."""
    for r in _REGISTRY:
        if r.id == rule_id:
            r.enabled = True
            return
    raise KeyError(f"Regel '{rule_id}' niet gevonden in de registry.")


# ---------------------------------------------------------------------------
# Lazy import van alle regelmodules
# ---------------------------------------------------------------------------

_rules_loaded = False


def _ensure_rules_loaded() -> None:
    global _rules_loaded
    if _rules_loaded:
        return
    import packages.rules.rules as _rules_pkg
    for _info in pkgutil.iter_modules(_rules_pkg.__path__):
        importlib.import_module(f"packages.rules.rules.{_info.name}")
    _rules_loaded = True
