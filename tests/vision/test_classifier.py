import cv2
import numpy as np

from ml.train_classifier import train
from packages.schema import SourceType, Symbol, SymbolType
from packages.vision.classifier import classify_candidates


def test_trained_classifier_retypes_and_rejects_without_moving(tmp_path):
    shape = np.full((48, 48), 255, np.uint8)
    cv2.circle(shape, (24, 24), 9, 0, 2)
    image = np.full((100, 160), 255, np.uint8)
    image[26:74, 16:64] = shape
    for name, crop in [("wandcontactdoos", shape), ("background", np.full_like(shape, 255))]:
        directory = tmp_path / "train" / name
        directory.mkdir(parents=True)
        (directory / "example.png").write_bytes(cv2.imencode(".png", crop)[1].tobytes())
    model = tmp_path / "classifier.npz"
    train(tmp_path, model)
    encoded = cv2.imencode(".png", image)[1].tobytes()
    symbols = [
        Symbol(type=SymbolType.SCHAKELAAR, x=x, y=100, source=SourceType.DETECTOR)
        for x in (80, 240)
    ]

    reviewed, summary = classify_candidates(encoded, symbols, str(model), 0.65, 2)

    assert [(item.type, item.x, item.y) for item in reviewed] == [(SymbolType.WANDCONTACTDOOS, 80, 100)]
    assert summary == {"candidates": 2, "background": 1, "unknown": 0}
    assert reviewed[0].attributes["classifier"]["previous_type"] == "schakelaar"

def test_classifier_exposes_uncertain_candidate_for_review(tmp_path):
    crop = np.full((48, 48), 255, np.uint8)
    data = cv2.imencode(".png", crop)[1].tobytes()
    for label in ("background", "wandcontactdoos"):
        directory = tmp_path / "train" / label
        directory.mkdir(parents=True)
        (directory / "same.png").write_bytes(data)
    model = tmp_path / "uncertain.npz"
    train(tmp_path, model)
    original = Symbol(type=SymbolType.SCHAKELAAR, x=24, y=24, source=SourceType.DETECTOR)

    reviewed, summary = classify_candidates(data, [original], str(model), 0.65, 1)

    assert reviewed[0].type == SymbolType.ONBEKEND
    assert reviewed[0].confidence == 0.5
    assert summary["unknown"] == 1 and summary["background"] == 0
