import numpy as np
import pandas as pd

from src.features.build_features import FEATURE_COLUMNS, build_features


def _toy_df(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(seed=0)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "station_id": [1] * n,
            "observed_date": dates,
            "temperature_c": rng.normal(10, 5, n),
            "humidity_pct": rng.integers(50, 90, n),
            "pressure_hpa": rng.normal(1015, 5, n),
            "wind_speed_ms": rng.uniform(0, 8, n),
            "precipitation_24h_mm": np.where(rng.random(n) > 0.7, rng.uniform(0, 20, n), 0.0),
            "latitude": [43.5] * n,
            "longitude": [3.9] * n,
            "altitude_m": [2] * n,
        }
    )


def test_build_features_produces_expected_columns():
    df = build_features(_toy_df())
    for col in FEATURE_COLUMNS:
        assert col in df.columns, f"Missing feature: {col}"


def test_build_features_target_is_binary():
    df = build_features(_toy_df())
    assert "target" in df.columns
    assert df["target"].isin([0, 1]).all()


def test_lag_uses_only_past_values():
    raw = _toy_df()
    df = build_features(raw).sort_values("observed_date").reset_index(drop=True)
    row = df.iloc[5]
    expected = (
        raw.sort_values("observed_date").reset_index(drop=True).iloc[4]["precipitation_24h_mm"]
    )
    assert abs(row["precip_lag_1"] - expected) < 1e-6


def test_target_is_next_day_rain_above_threshold():
    raw = _toy_df()
    df = build_features(raw).sort_values("observed_date").reset_index(drop=True)
    # ligne i a target = 1 ssi pluie(i+1) > 1mm
    next_precip = (
        raw.sort_values("observed_date").reset_index(drop=True)["precipitation_24h_mm"].shift(-1)
    )
    expected = (next_precip > 1.0).astype(int)
    assert (df["target"] == expected).all()


def test_seasonal_features_bounded():
    df = build_features(_toy_df())
    assert df["doy_sin"].between(-1, 1).all()
    assert df["doy_cos"].between(-1, 1).all()
    assert df["month"].between(1, 12).all()


def test_dropna_keeps_majority_of_rows():
    df = build_features(_toy_df(n=200)).dropna(subset=FEATURE_COLUMNS + ["target"])
    # On perd ~30 lignes (lag_7 + rolling_30 + target shift-1) sur 200 → garde ~170
    assert len(df) >= 150
