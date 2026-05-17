from datetime import date, datetime

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    station_id: int = Field(..., gt=0, description="Identifiant de la station")
    target_date: date = Field(..., description="Date pour laquelle prédire la pluie")


class PredictResponse(BaseModel):
    station_id: int
    station_name: str
    target_date: date
    predicted_proba: float = Field(..., ge=0.0, le=1.0)
    predicted_label: int = Field(..., ge=0, le=1)
    risk_level: str
    model_version: str
    computed_at: datetime


class StationOut(BaseModel):
    id: int
    synop_code: str
    name: str
    department: str | None
    latitude: float
    longitude: float


class HealthResponse(BaseModel):
    status: str
    model_version: str
    db: str
