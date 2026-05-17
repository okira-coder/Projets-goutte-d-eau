"""Service d'inférence : charge un bundle joblib et expose predict()."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np


def risk_level(proba: float) -> str:
    if proba < 0.3:
        return "bas"
    if proba < 0.6:
        return "modéré"
    return "élevé"


class ModelService:
    def __init__(self, model_path: str | Path) -> None:
        bundle = joblib.load(model_path)
        self.model = bundle["model"]
        self.features: list[str] = bundle["features"]
        self.version: str = bundle["version"]

    def predict(self, feature_vector: dict[str, float]) -> dict[str, Any]:
        x = np.array([[feature_vector.get(f, 0.0) for f in self.features]])
        proba = float(self.model.predict_proba(x)[0, 1])
        label = int(proba >= 0.5)
        return {
            "predicted_proba": round(proba, 4),
            "predicted_label": label,
            "risk_level": risk_level(proba),
            "model_version": self.version,
            "features_hash": self._hash(feature_vector),
        }

    def _hash(self, fv: dict[str, float]) -> str:
        canon = json.dumps(
            {k: fv.get(k) for k in self.features},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(canon.encode()).hexdigest()
