"""
packages/rules/rules/arei_art4.py
AREI Art. 4 — Bescherming van installatiedraden en -kabels / groepsleidingen.

Gedekte regels
--------------
AREI-4.4.2-WCD    Max wandcontactdozen per groepsleiding
AREI-4.4.2-LICHT  Max lichtpunten per groepsleiding
AREI-4.4.3-KRACHT Max krachtstopcontacten per groepsleiding
AREI-4-GROEP-LEEG Lege groep (circuit zonder verbruikers)
AREI-4-ONGEGROEP  Verbruikers zonder groepsindeling
"""

from __future__ import annotations

from collections import Counter, defaultdict

from packages.rules.engine import rule
from packages.rules.limits import RulesConfig
from packages.schema import Project, SymbolType, ValidationWarning

_LOAD_TYPES = {
    SymbolType.WANDCONTACTDOOS,
    SymbolType.LICHTPUNT,
    SymbolType.NOODVERLICHTING,
    SymbolType.THERMOSTAAT,
    SymbolType.ROOKMELDER,
    SymbolType.DATAPUNT,
}


@rule(
    id="AREI-4.4.2-WCD",
    description="Maximaal aantal wandcontactdozen per groepsleiding",
    article="AREI Art. 4.4.2 §2",
    source="AREI 2023",
    applies_to={"residential", "industrial", "commercial"},
)
def max_wcd_per_circuit(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    AREI Art. 4.4.2 §2 (editie 2023):
    'Per groepsleiding mogen niet meer dan 8 enkelvoudige contactdozen
    van 10/16 A worden aangesloten.'
    """
    limit = cfg.circuit.max_wcd
    counts: Counter[str] = Counter(
        s.circuit for s in p.symbols
        if s.circuit and s.type == SymbolType.WANDCONTACTDOOS
    )
    warnings = []
    for circuit, n in counts.items():
        if n > limit:
            ids = [
                s.id for s in p.symbols
                if s.circuit == circuit and s.type == SymbolType.WANDCONTACTDOOS
            ]
            warnings.append(ValidationWarning(
                code="AREI-4.4.2-WCD",
                severity="warning",
                message=(
                    f"Groep {circuit}: {n} wandcontactdozen "
                    f"(max {limit} per groepsleiding, AREI Art. 4.4.2 §2)."
                ),
                symbol_ids=ids,
            ))
    return warnings


@rule(
    id="AREI-4.4.2-LICHT",
    description="Maximaal aantal lichtpunten per groepsleiding",
    article="AREI Art. 4.4.2",
    source="AREI 2023",
    applies_to={"residential", "industrial", "commercial"},
)
def max_lichtpunten_per_circuit(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    limit = cfg.circuit.max_lichtpunten
    counts: Counter[str] = Counter(
        s.circuit for s in p.symbols
        if s.circuit and s.type == SymbolType.LICHTPUNT
    )
    warnings = []
    for circuit, n in counts.items():
        if n > limit:
            ids = [
                s.id for s in p.symbols
                if s.circuit == circuit and s.type == SymbolType.LICHTPUNT
            ]
            warnings.append(ValidationWarning(
                code="AREI-4.4.2-LICHT",
                severity="warning",
                message=(
                    f"Groep {circuit}: {n} lichtpunten "
                    f"(max {limit} aanbevolen per groepsleiding)."
                ),
                symbol_ids=ids,
            ))
    return warnings


@rule(
    id="AREI-4.4.3-KRACHT",
    description="Maximaal aantal krachtstopcontacten per groepsleiding",
    article="AREI Art. 4.4.3",
    source="AREI 2023",
    applies_to={"industrial", "commercial"},
)
def max_kracht_per_circuit(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    """
    AREI Art. 4.4.3 — krachtstopcontacten (16A/32A industrieel).
    Telt wandcontactdozen met attribute 'kracht'=True.
    """
    limit = cfg.circuit.max_kracht
    kracht_syms = [
        s for s in p.symbols
        if s.type == SymbolType.WANDCONTACTDOOS
        and s.attributes.get("kracht") is True
    ]
    if not kracht_syms:
        return []

    counts: Counter[str] = Counter(
        s.circuit for s in kracht_syms if s.circuit
    )
    warnings = []
    for circuit, n in counts.items():
        if n > limit:
            ids = [s.id for s in kracht_syms if s.circuit == circuit]
            warnings.append(ValidationWarning(
                code="AREI-4.4.3-KRACHT",
                severity="warning",
                message=(
                    f"Groep {circuit}: {n} krachtstopcontacten "
                    f"(max {limit} per groepsleiding, AREI Art. 4.4.3)."
                ),
                symbol_ids=ids,
            ))
    return warnings


@rule(
    id="AREI-4-GROEP-LEEG",
    description="Lege groep — circuit zonder verbruikers",
    article="AREI Art. 4",
    source="AREI 2023",
    severity="info",
    applies_to={"all"},
)
def lege_groep(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    circuit_types: dict[str, set[SymbolType]] = defaultdict(set)
    for s in p.symbols:
        if s.circuit:
            circuit_types[s.circuit].add(s.type)

    warnings = []
    for circuit, types in circuit_types.items():
        if not types & _LOAD_TYPES:
            warnings.append(ValidationWarning(
                code="AREI-4-GROEP-LEEG",
                severity="info",
                message=(
                    f"Groep {circuit} heeft geen verbruikers "
                    f"(alleen: {', '.join(t.value for t in types)})."
                ),
                symbol_ids=[s.id for s in p.symbols if s.circuit == circuit],
            ))
    return warnings


@rule(
    id="AREI-4-ONGEGROEP",
    description="Verbruikers zonder groepsindeling (circuit ontbreekt)",
    article="AREI Art. 4",
    source="AREI 2023",
    severity="info",
    applies_to={"all"},
)
def symbolen_zonder_circuit(p: Project, cfg: RulesConfig) -> list[ValidationWarning]:
    ungrouped = [
        s for s in p.symbols
        if s.type in _LOAD_TYPES and not s.circuit
    ]
    if not ungrouped:
        return []
    return [ValidationWarning(
        code="AREI-4-ONGEGROEP",
        severity="info",
        message=(
            f"{len(ungrouped)} verbruiker(s) zonder groepsindeling — "
            f"wijs een circuit toe (AREI Art. 4)."
        ),
        symbol_ids=[s.id for s in ungrouped],
    )]
