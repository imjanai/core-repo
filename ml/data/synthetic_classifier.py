"""Generate and train an isolated synthetic classifier smoke experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from ml.data.synthetic import generate_synthetic_blueprint
from ml.train_classifier import train
from packages.vision.classifier import BACKGROUND, symbol_crop
from packages.vision.detector import _heuristic

SIZE = 48


def build(output: Path, drawings: int) -> dict[str, int]:
    output.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(720)
    for index in range(drawings):
        # Golden drawings use seeds 900–905.
        project, source, _ = generate_synthetic_blueprint(f"classifier-{index}", seed=4000 + index)
        color = cv2.imdecode(np.frombuffer(source, np.uint8), cv2.IMREAD_COLOR)
        image = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
        centers = [(symbol.x / project.scale, symbol.y / project.scale, symbol.type.value)
                   for symbol in project.symbols]
        samples = []
        for x, y, label in centers:
            samples.extend([(x, y, label), (x + int(rng.integers(-4, 5)), y + int(rng.integers(-4, 5)), label)])
        for candidate in _heuristic(color):
            x, y = candidate.x, candidate.y
            nearest = min(centers, key=lambda center: (x - center[0])**2 + (y - center[1])**2)
            if (x - nearest[0])**2 + (y - nearest[1])**2 <= 9**2:
                samples.append((x, y, nearest[2]))
            elif all(abs(x - sx) > SIZE / 2 + 14 or abs(y - sy) > SIZE / 2 + 14 for sx, sy, _ in centers):
                samples.append((x, y, BACKGROUND))
        for number, (x, y, label) in enumerate(samples):
            target = output / "train" / label / f"{index:04d}-{number:03d}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(cv2.imencode(".png", symbol_crop(image, x, y, SIZE))[1].tobytes())
    return train(output, output / "classifier.npz")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--drawings", type=int, default=24, choices=range(1, 129), metavar="1..128")
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.drawings)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
