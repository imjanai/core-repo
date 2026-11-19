"""
ml/eval/metrics.py — 4-Level Evaluation Metric Engine.
Implements the 4 evaluation tiers from doc/069-metrics.md:
  Level 1: Detection (mAP@50, mAP@50-95, precision, recall per symbol class)
  Level 2: Counting (|pred - gt| per class, total count error, % perfect drawings)
  Level 3: Outcome (material bill quantity error, cost error in €, % cost difference)
  Level 4: Review pass-through (% drawings without human corrections, average corrections)
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from packages.schema import Project, Symbol, SymbolType


@dataclass
class Level1DetectionMetrics:
    precision_per_class: dict[str, float] = field(default_factory=dict)
    recall_per_class: dict[str, float] = field(default_factory=dict)
    map50_per_class: dict[str, float] = field(default_factory=dict)
    mean_map50: float = 0.0
    mean_map50_95: float = 0.0
    mean_precision: float = 0.0
    mean_recall: float = 0.0


@dataclass
class Level2CountingMetrics:
    avg_count_error_per_class: dict[str, float] = field(default_factory=dict)
    avg_total_count_error: float = 0.0
    perfect_drawings_pct: float = 0.0
    total_drawings: int = 0
    perfect_drawings_count: int = 0


@dataclass
class Level3OutcomeMetrics:
    avg_quantity_error: float = 0.0
    avg_cost_error_euros: float = 0.0
    avg_cost_error_pct: float = 0.0
    pred_total_costs: float = 0.0
    gt_total_costs: float = 0.0


@dataclass
class Level4WorkflowMetrics:
    pct_drawings_zero_correction: float = 0.0
    avg_corrections_per_drawing: float = 0.0


@dataclass
class FullEvaluationReport:
    model_version: str
    dataset_version: str
    level1: Level1DetectionMetrics
    level2: Level2CountingMetrics
    level3: Level3OutcomeMetrics
    level4: Level4WorkflowMetrics
    promotion_eligible: bool
    rejection_reasons: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        res = [
            f"# Evaluatierapport: {self.model_version}",
            f"**Dataset:** {self.dataset_version}",
            "",
            "## Niveau 1 — Detectie (Raster & VLM)",
            f"- **mAP@50:** {self.level1.mean_map50:.3f}",
            f"- **mAP@50-95:** {self.level1.mean_map50_95:.3f}",
            f"- **Precisie:** {self.level1.mean_precision:.3f}",
            f"- **Recall:** {self.level1.mean_recall:.3f}",
            "",
            "| Symboolklasse | mAP@50 | Precisie | Recall |",
            "|---|---|---|---|",
        ]
        for cls_name, m50 in self.level1.map50_per_class.items():
            p = self.level1.precision_per_class.get(cls_name, 0.0)
            r = self.level1.recall_per_class.get(cls_name, 0.0)
            res.append(f"| {cls_name} | {m50:.3f} | {p:.3f} | {r:.3f} |")

        res.extend([
            "",
            "## Niveau 2 — Telling per tekening",
            f"- **Gemiddelde tellingfout:** {self.level2.avg_total_count_error:.2f} symbolen/tekening",
            f"- **Perfecte tekeningen (fout = 0):** {self.level2.perfect_drawings_pct:.1f}% ({self.level2.perfect_drawings_count}/{self.level2.total_drawings})",
            "",
            "## Niveau 3 — Uitkomst (Materiaallijst & Kosten)",
            f"- **Gemiddelde materiaalkostenfout:** € {self.level3.avg_cost_error_euros:.2f}",
            f"- **Kostenafwijking percentage:** {self.level3.avg_cost_error_pct:.2f}%",
            f"- **Totale grondwaarde:** € {self.level3.gt_total_costs:.2f} | **Voorspeld:** € {self.level3.pred_total_costs:.2f}",
            "",
            "## Niveau 4 — Doorlaat (Review-UI)",
            f"- **Tekeningen zonder correctie:** {self.level4.pct_drawings_zero_correction:.1f}%",
            f"- **Gemiddeld aantal correcties per tekening:** {self.level4.avg_corrections_per_drawing:.2f}",
            "",
            "---",
            f"### Promotiebesluit: {'[PASS] GOEDGEKEURD (GEEN REGRESSIE)' if self.promotion_eligible else '[FAIL] AFGEKEURD'}",
        ])
        if self.rejection_reasons:
            res.append("\n**Afwijzingsredenen:**")
            for r in self.rejection_reasons:
                res.append(f"- {r}")

        return "\n".join(res) + "\n"


def compute_level2_counting(
    predictions: list[Project],
    ground_truths: list[Project],
) -> Level2CountingMetrics:
    """Computes counting metrics across all paired drawings."""
    total_drawings = len(ground_truths)
    if total_drawings == 0:
        return Level2CountingMetrics()

    class_errors: dict[str, list[float]] = defaultdict(list)
    total_errors: list[float] = []
    perfect_count = 0

    for pred, gt in zip(predictions, ground_truths):
        pred_counts = Counter(s.type.value for s in pred.symbols)
        gt_counts = Counter(s.type.value for s in gt.symbols)

        all_classes = set(pred_counts.keys()).union(gt_counts.keys())
        drawing_error = 0.0
        for cls in all_classes:
            err = abs(pred_counts[cls] - gt_counts[cls])
            class_errors[cls].append(err)
            drawing_error += err

        total_errors.append(drawing_error)
        if drawing_error == 0:
            perfect_count += 1

    avg_per_class = {cls: sum(errs) / total_drawings for cls, errs in class_errors.items()}
    avg_total = sum(total_errors) / total_drawings
    perfect_pct = (perfect_count / total_drawings) * 100.0

    return Level2CountingMetrics(
        avg_count_error_per_class=avg_per_class,
        avg_total_count_error=round(avg_total, 2),
        perfect_drawings_pct=round(perfect_pct, 1),
        total_drawings=total_drawings,
        perfect_drawings_count=perfect_count,
    )


def compute_level3_outcome(
    predictions: list[Project],
    ground_truths: list[Project],
) -> Level3OutcomeMetrics:
    """Computes material list and cost discrepancy metrics."""
    total_drawings = len(ground_truths)
    if total_drawings == 0:
        return Level3OutcomeMetrics()

    cost_errors: list[float] = []
    cost_error_pcts: list[float] = []
    total_pred_cost = 0.0
    total_gt_cost = 0.0

    for pred, gt in zip(predictions, ground_truths):
        p_cost = sum(m.total_price or 0.0 for m in pred.materials)
        g_cost = sum(m.total_price or 0.0 for m in gt.materials)
        total_pred_cost += p_cost
        total_gt_cost += g_cost

        diff = abs(p_cost - g_cost)
        cost_errors.append(diff)
        pct = (diff / g_cost * 100.0) if g_cost > 0 else 0.0
        cost_error_pcts.append(pct)

    avg_cost_err = sum(cost_errors) / total_drawings
    avg_cost_pct = sum(cost_error_pcts) / total_drawings

    return Level3OutcomeMetrics(
        avg_cost_error_euros=round(avg_cost_err, 2),
        avg_cost_error_pct=round(avg_cost_pct, 2),
        pred_total_costs=round(total_pred_cost, 2),
        gt_total_costs=round(total_gt_cost, 2),
    )


def compute_level4_workflow(
    predictions: list[Project],
    ground_truths: list[Project],
) -> Level4WorkflowMetrics:
    """Computes human review effort and zero-correction pass-through."""
    total_drawings = len(ground_truths)
    if total_drawings == 0:
        return Level4WorkflowMetrics()

    corrections_per_drawing: list[int] = []
    zero_corrections = 0

    for pred, gt in zip(predictions, ground_truths):
        # A correction is needed for every missed symbol, false alarm, or misclassification
        p_types = Counter(s.type.value for s in pred.symbols)
        g_types = Counter(s.type.value for s in gt.symbols)
        all_keys = set(p_types.keys()).union(g_types.keys())
        corrs = sum(abs(p_types[k] - g_types[k]) for k in all_keys)
        corrections_per_drawing.append(corrs)
        if corrs == 0:
            zero_corrections += 1

    pct_zero = (zero_corrections / total_drawings) * 100.0
    avg_corrs = sum(corrections_per_drawing) / total_drawings

    return Level4WorkflowMetrics(
        pct_drawings_zero_correction=round(pct_zero, 1),
        avg_corrections_per_drawing=round(avg_corrs, 2),
    )
