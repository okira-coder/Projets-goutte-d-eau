"""
Entraînement : LogisticRegression baseline + XGBoost.
Split temporel 80/20, TimeSeriesSplit pour la CV, persist via joblib.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.db.connection import engine
from src.features.build_features import (
    FEATURE_COLUMNS,
    build_features,
    load_daily_from_db,
)

logger = logging.getLogger(__name__)
MODELS_DIR = Path("models")
REPORTS_DIR = Path("reports")


def temporal_split(df: pd.DataFrame, ratio: float = 0.8) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.sort_values("observed_date")
    cutoff = df["observed_date"].quantile(ratio)
    train = df[df["observed_date"] <= cutoff]
    test = df[df["observed_date"] > cutoff]
    return train, test


def evaluate(y_true, y_pred, y_proba) -> dict[str, float]:
    return {
        "roc_auc": float(roc_auc_score(y_true, y_proba)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "brier": float(brier_score_loss(y_true, y_proba)),
        "n_positive": int(y_true.sum()),
        "n_total": int(len(y_true)),
    }


def train_logreg(X_train, y_train) -> Pipeline:
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42),
            ),
        ]
    )
    pipe.fit(X_train, y_train)
    return pipe


def train_xgboost(X_train, y_train):
    from xgboost import XGBClassifier  # lazy import (needs libomp at runtime)

    pos = int((y_train == 1).sum())
    neg = int((y_train == 0).sum())
    spw = neg / max(pos, 1)
    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.8,
        scale_pos_weight=spw,
        eval_metric="auc",
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train)
    return model


def cross_validate_auc(model_builder, X, y, n_splits: int = 5) -> list[float]:
    tscv = TimeSeriesSplit(n_splits=n_splits)
    aucs: list[float] = []
    for tr, te in tscv.split(X):
        m = model_builder(X[tr], y[tr])
        if hasattr(m, "predict_proba"):
            p = m.predict_proba(X[te])[:, 1]
        else:
            p = m.predict(X[te])
        aucs.append(float(roc_auc_score(y[te], p)))
    return aucs


def main() -> dict[str, dict[str, float]]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    MODELS_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)

    logger.info("Chargement données…")
    daily = load_daily_from_db(engine)
    if daily.empty:
        raise RuntimeError("Aucune donnée disponible — lancer d'abord 'make ingest'")
    feats = build_features(daily).dropna(subset=FEATURE_COLUMNS + ["target"])
    logger.info("Total lignes utilisables: %d", len(feats))

    train_df, test_df = temporal_split(feats, 0.8)
    X_train = train_df[FEATURE_COLUMNS].to_numpy()
    y_train = train_df["target"].to_numpy()
    X_test = test_df[FEATURE_COLUMNS].to_numpy()
    y_test = test_df["target"].to_numpy()
    logger.info(
        "Train=%d  Test=%d  Taux pluie train=%.2f",
        len(X_train),
        len(X_test),
        float(y_train.mean()),
    )

    # LogReg baseline
    logreg = train_logreg(X_train, y_train)
    y_proba_lr = logreg.predict_proba(X_test)[:, 1]
    y_pred_lr = (y_proba_lr >= 0.5).astype(int)
    m_lr = evaluate(y_test, y_pred_lr, y_proba_lr)
    logger.info("LogReg: %s", m_lr)
    joblib.dump(
        {"model": logreg, "features": FEATURE_COLUMNS, "version": "lr-1.0.0"},
        MODELS_DIR / "baseline.pkl",
    )

    # XGBoost
    xgb = train_xgboost(X_train, y_train)
    y_proba_xgb = xgb.predict_proba(X_test)[:, 1]
    y_pred_xgb = (y_proba_xgb >= 0.5).astype(int)
    m_xgb = evaluate(y_test, y_pred_xgb, y_proba_xgb)
    logger.info("XGBoost: %s", m_xgb)
    joblib.dump(
        {"model": xgb, "features": FEATURE_COLUMNS, "version": "xgb-1.0.0"},
        MODELS_DIR / "xgboost.pkl",
    )

    cv_xgb = cross_validate_auc(train_xgboost, X_train, y_train)
    cm_xgb = confusion_matrix(y_test, y_pred_xgb).tolist()
    logger.info("CV AUC XGB: mean=%.3f std=%.3f", np.mean(cv_xgb), np.std(cv_xgb))
    logger.info("Confusion XGB: %s", cm_xgb)

    summary = {
        "logreg": m_lr,
        "xgboost": m_xgb,
        "xgb_cv_auc_mean": float(np.mean(cv_xgb)),
        "xgb_cv_auc_std": float(np.std(cv_xgb)),
        "confusion_xgb": cm_xgb,
    }
    (REPORTS_DIR / "training_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
