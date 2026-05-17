from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from src.models.predict import ModelService, risk_level


def test_risk_level_thresholds():
    assert risk_level(0.0) == "bas"
    assert risk_level(0.1) == "bas"
    assert risk_level(0.29) == "bas"
    assert risk_level(0.3) == "modéré"
    assert risk_level(0.45) == "modéré"
    assert risk_level(0.59) == "modéré"
    assert risk_level(0.6) == "élevé"
    assert risk_level(0.9) == "élevé"


def test_model_service_loads_and_predicts(tmp_path: Path):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(100, 3))
    y = (X[:, 0] > 0).astype(int)
    model = LogisticRegression().fit(X, y)
    bundle = {"model": model, "features": ["a", "b", "c"], "version": "test-0.1"}
    p = tmp_path / "m.pkl"
    joblib.dump(bundle, p)
    svc = ModelService(p)
    out = svc.predict({"a": 1.0, "b": -0.5, "c": 0.2})
    assert 0.0 <= out["predicted_proba"] <= 1.0
    assert out["predicted_label"] in (0, 1)
    assert out["model_version"] == "test-0.1"
    assert len(out["features_hash"]) == 64


def _toy_two_class_model() -> LogisticRegression:
    X = np.array([[0.0], [1.0], [2.0], [3.0]])
    y = np.array([0, 0, 1, 1])
    return LogisticRegression().fit(X, y)


def test_features_hash_is_deterministic(tmp_path: Path):
    bundle = {"model": _toy_two_class_model(), "features": ["x"], "version": "t"}
    p = tmp_path / "m.pkl"
    joblib.dump(bundle, p)
    svc = ModelService(p)
    h1 = svc.predict({"x": 1.23})["features_hash"]
    h2 = svc.predict({"x": 1.23})["features_hash"]
    h3 = svc.predict({"x": 1.24})["features_hash"]
    assert h1 == h2
    assert h1 != h3


def test_features_hash_only_uses_known_features(tmp_path: Path):
    bundle = {"model": _toy_two_class_model(), "features": ["x"], "version": "t"}
    p = tmp_path / "m.pkl"
    joblib.dump(bundle, p)
    svc = ModelService(p)
    h1 = svc.predict({"x": 1.0})["features_hash"]
    h2 = svc.predict({"x": 1.0, "extra": 999.0})["features_hash"]
    assert h1 == h2
