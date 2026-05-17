from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.schemas import (
    HealthResponse,
    PredictRequest,
    PredictResponse,
    StationOut,
)
from src.config import settings
from src.db.connection import SessionLocal
from src.db.repository import ObservationRepository, StationRepository
from src.features.build_features import FEATURE_COLUMNS, build_features
from src.models.predict import ModelService

logger = logging.getLogger(__name__)
router = APIRouter()

_model_service: ModelService | None = None


def get_session():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def get_model() -> ModelService:
    global _model_service
    if _model_service is None:
        _model_service = ModelService(settings.model_path)
    return _model_service


@router.get("/health", response_model=HealthResponse)
def health(session: Session = Depends(get_session)) -> HealthResponse:
    try:
        session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        logger.warning("DB check failed: %s", exc)
        db_status = "error"
    try:
        version = get_model().version
    except Exception as exc:
        logger.warning("Model load failed: %s", exc)
        version = "unloaded"
    status = "ok" if db_status == "connected" and version != "unloaded" else "degraded"
    return HealthResponse(status=status, model_version=version, db=db_status)


@router.get("/stations", response_model=list[StationOut])
def list_stations(session: Session = Depends(get_session)) -> list[StationOut]:
    repo = StationRepository(session)
    return [StationOut(**s) for s in repo.list_all()]


@router.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest, session: Session = Depends(get_session)) -> PredictResponse:
    today = datetime.now(timezone.utc).date()
    if req.target_date > today + timedelta(days=7):
        raise HTTPException(422, detail="target_date must be ≤ J+7")
    # Pas de borne basse stricte : permet la prédiction rétroactive sur l'historique
    # (utile pour démo + backtesting). En prod, restreindre selon le besoin métier.

    station_repo = StationRepository(session)
    obs_repo = ObservationRepository(session)
    stations = {s["id"]: s for s in station_repo.list_all()}
    if req.station_id not in stations:
        raise HTTPException(404, detail="Unknown station_id")
    station = stations[req.station_id]

    # Fenêtre large : 90 jours × 8 obs/j (rolling 30j a besoin de 30j d'historique
    # post-target_date, et il peut y avoir des trous dans les SYNOP)
    obs = obs_repo.fetch_for_station(req.station_id, limit=720)
    if not obs:
        raise HTTPException(503, detail="No observations available")

    df = pd.DataFrame(obs)
    df["observed_date"] = pd.to_datetime(df["observed_at"]).dt.normalize()
    df["station_id"] = req.station_id
    daily = (
        df.groupby(["station_id", "observed_date"], as_index=False)
        .agg(
            {
                "temperature_c": "mean",
                "humidity_pct": "mean",
                "pressure_hpa": "mean",
                "wind_speed_ms": "mean",
                "precipitation_3h_mm": "sum",
            }
        )
        .rename(columns={"precipitation_3h_mm": "precipitation_24h_mm"})
    )
    daily["latitude"] = station["latitude"]
    daily["longitude"] = station["longitude"]
    daily["altitude_m"] = station["altitude_m"]

    feats = build_features(daily).dropna(subset=FEATURE_COLUMNS)
    if feats.empty:
        raise HTTPException(503, detail="Not enough history to build features")

    latest = feats.iloc[-1][FEATURE_COLUMNS].to_dict()
    pred = get_model().predict(latest)

    # Audit log
    try:
        session.execute(
            text("""INSERT INTO predictions
                     (station_id, target_date, predicted_proba, predicted_label,
                      model_version, features_hash)
                   VALUES (:s, :d, :p, :l, :v, :h)"""),
            {
                "s": req.station_id,
                "d": req.target_date,
                "p": pred["predicted_proba"],
                "l": pred["predicted_label"],
                "v": pred["model_version"],
                "h": pred["features_hash"],
            },
        )
        session.commit()
    except Exception as exc:
        logger.warning("Failed to log prediction: %s", exc)
        session.rollback()

    return PredictResponse(
        station_id=req.station_id,
        station_name=station["name"],
        target_date=req.target_date,
        predicted_proba=pred["predicted_proba"],
        predicted_label=pred["predicted_label"],
        risk_level=pred["risk_level"],
        model_version=pred["model_version"],
        computed_at=datetime.now(timezone.utc),
    )
