"""Tests training avec toy data — pas besoin de MySQL.

Skippe les tests XGBoost si libxgboost ne peut pas se charger (libomp manquant sur macOS).
"""

import numpy as np
import pandas as pd
import pytest

from src.models.train import evaluate, temporal_split, train_logreg


def _xgboost_available() -> bool:
    try:
        import xgboost as xgb

        xgb.XGBClassifier()
        return True
    except Exception:
        return False


xgb_skip = pytest.mark.skipif(not _xgboost_available(), reason="xgboost ou libomp non disponible")


def _toy_xy(n: int = 300, seed: int = 0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 5))
    y = (X[:, 0] + 0.5 * X[:, 1] + rng.normal(scale=0.3, size=n) > 0).astype(int)
    return X, y


def test_train_logreg_runs_and_evaluates():
    X, y = _toy_xy()
    model = train_logreg(X, y)
    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= 0.5).astype(int)
    metrics = evaluate(y, pred, proba)
    assert metrics["roc_auc"] > 0.7
    assert 0 <= metrics["f1"] <= 1
    assert metrics["n_total"] == len(y)


@xgb_skip
def test_train_xgboost_runs_and_evaluates():
    from src.models.train import train_xgboost

    X, y = _toy_xy()
    model = train_xgboost(X, y)
    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= 0.5).astype(int)
    metrics = evaluate(y, pred, proba)
    assert metrics["roc_auc"] > 0.7


def test_temporal_split_no_overlap():
    df = pd.DataFrame(
        {
            "observed_date": pd.date_range("2024-01-01", periods=100, freq="D"),
            "val": range(100),
        }
    )
    train, test = temporal_split(df, 0.8)
    assert train["observed_date"].max() <= test["observed_date"].min()
    assert len(train) + len(test) == len(df)
    assert len(train) > len(test)


def test_evaluate_returns_expected_keys():
    rng = np.random.default_rng(0)
    y_true = rng.integers(0, 2, 50)
    y_proba = rng.random(50)
    y_pred = (y_proba >= 0.5).astype(int)
    out = evaluate(y_true, y_pred, y_proba)
    for k in ["roc_auc", "f1", "precision", "recall", "brier", "n_positive", "n_total"]:
        assert k in out
