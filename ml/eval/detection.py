"""Point-based detection metrics for symbol annotations."""

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from math import floor, hypot, isfinite

from packages.schema import Symbol


@dataclass
class ClassCounts:
    correct: int = 0
    predicted: int = 0
    expected: int = 0

    @property
    def precision(self) -> float:
        return self.correct / self.predicted if self.predicted else 0.0

    @property
    def recall(self) -> float:
        return self.correct / self.expected if self.expected else 0.0

    @property
    def f1(self) -> float:
        denominator = self.predicted + self.expected
        return 2 * self.correct / denominator if denominator else 0.0


@dataclass
class DrawingErrors:
    filename: str
    tolerance: float
    correct: int
    misses: list[dict]
    false_positives: list[dict]
    wrong_types: list[dict]
    detector: str
    vlm: str
    classifier: dict = field(default_factory=dict)
    tile_count: int = 0

    @property
    def corrections(self) -> int:
        return len(self.misses) + len(self.false_positives) + len(self.wrong_types)


@dataclass
class Level1DetectionMetrics:
    overall: ClassCounts = field(default_factory=ClassCounts)
    by_class: dict[str, ClassCounts] = field(default_factory=dict)
    drawings: list[DrawingErrors] = field(default_factory=list)


def _match(
    predicted: list[Symbol], expected: list[Symbol], tolerance: float, *, same_type: bool,
) -> dict[int, int]:
    """Find a maximum-cardinality one-to-one match inside the position tolerance."""
    grid = defaultdict(list)
    for index, symbol in enumerate(expected):
        grid[floor(symbol.x / tolerance), floor(symbol.y / tolerance)].append(index)

    neighbours = {}
    for left, pred in enumerate(predicted):
        col, row = floor(pred.x / tolerance), floor(pred.y / tolerance)
        matches = []
        for x in range(col - 1, col + 2):
            for y in range(row - 1, row + 2):
                for right in grid.get((x, y), ()):
                    target = expected[right]
                    if same_type and pred.type != target.type:
                        continue
                    distance = hypot(pred.x - target.x, pred.y - target.y)
                    if distance <= tolerance:
                        matches.append((distance, right))
        neighbours[left] = [right for _, right in sorted(matches)]

    matched_left, matched_right = {}, {}
    for start in range(len(predicted)):
        frontier = deque([start])
        visited_left = {start}
        visited_right = {}
        while frontier:
            left = frontier.popleft()
            found = False
            for right in neighbours[left]:
                if right in visited_right:
                    continue
                visited_right[right] = left
                owner = matched_right.get(right)
                if owner is None:
                    while right is not None:
                        new_owner = visited_right[right]
                        old_right = matched_left.get(new_owner)
                        matched_left[new_owner] = right
                        matched_right[right] = new_owner
                        right = old_right
                    found = True
                    break
                if owner not in visited_left:
                    visited_left.add(owner)
                    frontier.append(owner)
            if found:
                break
    return matched_left


def _symbol(symbol: Symbol) -> dict:
    return {"type": symbol.type.value, "x": symbol.x, "y": symbol.y, "source": symbol.source.value}


def record_drawing(
    metrics: Level1DetectionMetrics, filename: str, predicted: list[Symbol],
    expected: list[Symbol], tolerance: float, *, detector: str, vlm: str,
) -> None:
    if not isfinite(tolerance) or tolerance <= 0:
        raise ValueError("Position tolerance must be positive and finite")
    if any(not isfinite(s.x) or not isfinite(s.y) for s in [*predicted, *expected]):
        raise ValueError(f"{filename}: symbol coordinates must be finite")

    correct = _match(predicted, expected, tolerance, same_type=True)
    matched_expected = set(correct.values())
    remaining_pred = [symbol for index, symbol in enumerate(predicted) if index not in correct]
    remaining_gt = [symbol for index, symbol in enumerate(expected) if index not in matched_expected]
    mixups = _match(remaining_pred, remaining_gt, tolerance, same_type=False)
    wrong_targets = set(mixups.values())
    metrics.drawings.append(DrawingErrors(
        filename=filename, tolerance=tolerance, correct=len(correct),
        misses=[_symbol(s) for i, s in enumerate(remaining_gt) if i not in wrong_targets],
        false_positives=[_symbol(s) for i, s in enumerate(remaining_pred) if i not in mixups],
        wrong_types=[
            {"expected": _symbol(remaining_gt[right]), "predicted": _symbol(remaining_pred[left])}
            for left, right in mixups.items()
        ],
        detector=detector, vlm=vlm,
    ))
    pred_counts = Counter(s.type.value for s in predicted)
    gt_counts = Counter(s.type.value for s in expected)
    correct_counts = Counter(predicted[i].type.value for i in correct)
    for name in pred_counts.keys() | gt_counts.keys():
        counts = metrics.by_class.setdefault(name, ClassCounts())
        counts.correct += correct_counts[name]
        counts.predicted += pred_counts[name]
        counts.expected += gt_counts[name]
    metrics.overall.correct += len(correct)
    metrics.overall.predicted += len(predicted)
    metrics.overall.expected += len(expected)
