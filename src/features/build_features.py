"""
Source unique de vérité (SSOT) des features.

Cette fonction est utilisée identiquement en TRAINING et en INFERENCE
pour garantir l'absence de skew train/serve.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RAW_COLUMNS = [
    "temperature_c",
    "humidity_pct",
    "pressure_hpa",
    "wind_speed_ms",
    "precipitation_24h_mm",
]

LAG_DAYS = [1, 2, 3, 7]
ROLLING_WINDOWS = [7, 30]

FEATURE_COLUMNS: list[str] = (
    RAW_COLUMNS
    + [f"precip_lag_{d}" for d in LAG_DAYS]
    + [f"pressure_lag_{d}" for d in LAG_DAYS]
    + [f"temp_lag_{d}" for d in LAG_DAYS]
    + [f"precip_mean_{w}d" for w in ROLLING_WINDOWS]
    + [f"precip_std_{w}d" for w in ROLLING_WINDOWS]
    + [f"pressure_mean_{w}d" for w in ROLLING_WINDOWS]
    + ["pressure_diff_24h", "humidity_diff_24h"]
    + ["doy_sin", "doy_cos", "month"]
    + ["latitude", "longitude", "altitude_m"]
)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Construit features et target depuis un DataFrame quotidien par station.

    Colonnes d'entrée attendues :
        station_id, observed_date, latitude, longitude, altitude_m,
        temperature_c, humidity_pct, pressure_hpa, wind_speed_ms,
        precipitation_24h_mm

    Ajoute toutes les colonnes de FEATURE_COLUMNS + 'target' (1 si pluie J+1 > 1mm).
    """
    df = df.copy().sort_values(["station_id", "observed_date"]).reset_index(drop=True)

    # Convertir en numérique pour les decimals MySQL
    for col in RAW_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Lags
    grp_precip = df.groupby("station_id")["precipitation_24h_mm"]
    grp_pressure = df.groupby("station_id")["pressure_hpa"]
    grp_temp = df.groupby("station_id")["temperature_c"]
    for d in LAG_DAYS:
        df[f"precip_lag_{d}"] = grp_precip.shift(d)
        df[f"pressure_lag_{d}"] = grp_pressure.shift(d)
        df[f"temp_lag_{d}"] = grp_temp.shift(d)

    # Rolling (sur valeurs passées : shift(1) puis rolling)
    for w in ROLLING_WINDOWS:
        df[f"precip_mean_{w}d"] = df.groupby("station_id")["precipitation_24h_mm"].transform(
            lambda s, w=w: s.shift(1).rolling(w, min_periods=1).mean()
        )
        df[f"precip_std_{w}d"] = df.groupby("station_id")["precipitation_24h_mm"].transform(
            lambda s, w=w: s.shift(1).rolling(w, min_periods=2).std()
        )
        df[f"pressure_mean_{w}d"] = df.groupby("station_id")["pressure_hpa"].transform(
            lambda s, w=w: s.shift(1).rolling(w, min_periods=1).mean()
        )

    # Différentielles 24h
    df["pressure_diff_24h"] = df.groupby("station_id")["pressure_hpa"].diff(1)
    df["humidity_diff_24h"] = df.groupby("station_id")["humidity_pct"].diff(1)

    # Saisonnier
    doy = df["observed_date"].dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    df["month"] = df["observed_date"].dt.month

    # Target : pluie significative J+1 (> 1mm)
    df["target"] = (df.groupby("station_id")["precipitation_24h_mm"].shift(-1) > 1.0).astype(int)

    return df


def load_daily_from_db(engine) -> pd.DataFrame:
    """Agrège les observations 3h en quotidien (somme pluie, moyenne autres).

    Fonctionne aussi bien avec MySQL qu'avec SQLite : la fonction DATE() existe
    dans les deux dialectes (et SQLite accepte les TIMESTAMP ISO-8601).
    """
    query = """
    SELECT
      s.id AS station_id,
      s.latitude AS latitude,
      s.longitude AS longitude,
      s.altitude_m AS altitude_m,
      DATE(o.observed_at) AS observed_date,
      AVG(o.temperature_c) AS temperature_c,
      AVG(o.humidity_pct) AS humidity_pct,
      AVG(o.pressure_hpa) AS pressure_hpa,
      AVG(o.wind_speed_ms) AS wind_speed_ms,
      SUM(o.precipitation_3h_mm) AS precipitation_24h_mm
    FROM observations o
    JOIN stations s ON s.id = o.station_id
    WHERE s.region = 'Occitanie'
    GROUP BY s.id, DATE(o.observed_at)
    """
    df = pd.read_sql(query, engine)
    df["observed_date"] = pd.to_datetime(df["observed_date"])
    # Convertir les decimals SQL en floats pour pandas/numpy
    for col in [
        "latitude",
        "longitude",
        "temperature_c",
        "humidity_pct",
        "pressure_hpa",
        "wind_speed_ms",
        "precipitation_24h_mm",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
