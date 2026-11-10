"""Classifier tests — TensorFlow model trained on synthetic patterns.
Skipped with a clear message if TensorFlow is not installed (the model is
then unavailable and the backend refuses to start payments).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

tf = pytest.importorskip("tensorflow", reason="TensorFlow not installed")

from classifier import Classifier, generate_synthetic  # noqa: E402
from policy import features  # noqa: E402


def test_synthetic_data_shapes():
    X, y = generate_synthetic()
    assert X.shape == (2400, 5)
    assert y.shape == (2400,)
    assert set(y.tolist()) == {0.0, 1.0}


def test_train_produces_honest_metrics(tmp_path, monkeypatch):
    import classifier as clf_mod
    monkeypatch.setattr(clf_mod, "MODEL_DIR", tmp_path)
    metrics = clf_mod.train(epochs=10)
    assert metrics["test_accuracy"] > 0.85
    assert metrics["legit_accuracy"] > 0.85
    assert metrics["attack_accuracy"] > 0.85
    assert (tmp_path / "classifier.keras").exists()
    assert (tmp_path / "metrics.json").exists()


def test_classifier_scores_legit_low_and_attack_high():
    clf = Classifier()
    legit = features(0.5, True, 2.0, 9.0, 0)
    drain = features(50.0, False, 2.0, 9.0, 0)
    overcap = features(3.0, True, 2.0, 9.0, 0)
    burst = features(0.2, True, 2.0, 9.0, 5)
    assert clf.score(legit) < 0.5, f"legit scored {clf.score(legit)}"
    assert clf.score(drain) >= 0.5, f"drain scored {clf.score(drain)}"
    assert clf.score(overcap) >= 0.5, f"overcap scored {clf.score(overcap)}"
    assert clf.score(burst) >= 0.5, f"burst scored {clf.score(burst)}"
