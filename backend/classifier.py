"""Small TensorFlow classifier: pre-screen score P(attack) beside the rule verdict.

Trained ONLY on synthetic patterns generated locally (no external dataset):
  legit  — small amounts, allowlisted recipient, within caps, low velocity
  attack — large amounts, non-allowlisted recipient, over-cap ratios, bursts
Features (see policy.features): [log1p(amount), allowlisted, amount/cap,
amount/daily_remaining, recent_count/3]. A tiny dense net (16 -> 8 -> 1).
The model is a *pre-screen*: it can only QUEUE a payment for human review,
never block or execute on its own — the rules + the on-chain contract decide.
"""
import json
import math
import os
import random
from pathlib import Path

import numpy as np

MODEL_DIR = Path(__file__).parent / "model"

FEATURES = ["log1p_amount", "allowlisted", "amount_over_cap",
            "amount_over_daily_remaining", "velocity"]


def generate_synthetic(n_legit=1200, n_attack=1200, seed=7):
    rng = random.Random(seed)
    X, y = [], []
    for _ in range(n_legit):
        amount = rng.uniform(0.05, 2.0)  # up to the per-tx cap: a legit
        # payment may be large; size alone must not flag it
        cap = 2.0
        daily_remaining = rng.uniform(2.0, 10.0)
        X.append([math.log1p(amount), 1.0, min(amount / cap, 5.0),
                  min(amount / daily_remaining, 5.0),
                  min(rng.choice([0, 0, 1, 1, 2]) / 3.0, 3.0)])
        y.append(0)
    for _ in range(n_attack):
        kind = rng.choice(["drain", "overcap", "burst"])
        if kind == "drain":
            amount = rng.uniform(5.0, 100.0)
            X.append([math.log1p(amount), 0.0, min(amount / 2.0, 5.0),
                      min(amount / rng.uniform(0.5, 5.0), 5.0),
                      min(rng.choice([0, 1]) / 3.0, 3.0)])
        elif kind == "overcap":
            amount = rng.uniform(2.1, 8.0)
            X.append([math.log1p(amount), 1.0, min(amount / 2.0, 5.0),
                      min(amount / rng.uniform(1.0, 5.0), 5.0),
                      min(rng.choice([0, 1, 2]) / 3.0, 3.0)])
        else:  # burst
            amount = rng.uniform(0.1, 1.5)
            X.append([math.log1p(amount), 1.0, min(amount / 2.0, 5.0),
                      min(amount / rng.uniform(2.0, 10.0), 5.0),
                      min(rng.choice([3, 4, 5, 6]) / 3.0, 3.0)])
        y.append(1)
    idx = list(range(len(X)))
    rng.shuffle(idx)
    return np.array([X[i] for i in idx], dtype=np.float32), np.array([y[i] for i in idx], dtype=np.float32)


def build_model():
    import tensorflow as tf
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(16, activation="relu", input_shape=(5,)),
        tf.keras.layers.Dense(8, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def train(seed=7, epochs=60):
    import tensorflow as tf
    tf.random.set_seed(seed)
    X, y = generate_synthetic(seed=seed)
    split = int(0.8 * len(X))
    X_train, y_train, X_test, y_test = X[:split], y[:split], X[split:], y[split:]
    model = build_model()
    model.fit(X_train, y_train, epochs=epochs, batch_size=32, verbose=0)
    loss, acc = model.evaluate(X_test, y_test, verbose=0)
    # Per-class accuracy on the held-out set (honest breakdown, not just overall).
    preds = (model.predict(X_test, verbose=0).flatten() >= 0.5).astype(int)
    legit_acc = float(np.mean(preds[y_test == 0] == 0))
    attack_acc = float(np.mean(preds[y_test == 1] == 1))
    metrics = {"test_accuracy": round(float(acc), 4),
               "legit_accuracy": round(legit_acc, 4),
               "attack_accuracy": round(attack_acc, 4),
               "test_samples": int(len(X_test)), "epochs": epochs, "seed": seed}
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save(str(MODEL_DIR / "classifier.keras"))
    (MODEL_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics


class Classifier:
    """Loads the trained model; falls back to training if absent."""

    def __init__(self, model_dir: str | Path = MODEL_DIR):
        self.model_dir = Path(model_dir)
        model_path = self.model_dir / "classifier.keras"
        if not model_path.exists():
            train()
        import tensorflow as tf
        self.model = tf.keras.models.load_model(str(model_path))

    def score(self, feature_vector) -> float:
        import numpy as np
        x = np.array([feature_vector], dtype=np.float32)
        return float(self.model.predict(x, verbose=0).flatten()[0])


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
