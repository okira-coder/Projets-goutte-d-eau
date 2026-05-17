"""
Tests d'intégration repository — nécessitent MySQL running + schéma initialisé.
Skippe si la BDD n'est pas joignable.
"""

from datetime import datetime

import pytest
from sqlalchemy.exc import OperationalError

from src.db.connection import SessionLocal
from src.db.repository import ObservationRepository, StationRepository


@pytest.fixture
def session():
    s = SessionLocal()
    try:
        s.execute(__import__("sqlalchemy").text("SELECT 1"))
    except OperationalError:
        pytest.skip("MySQL non disponible")
    try:
        yield s
    finally:
        s.rollback()
        s.close()


def test_list_stations_returns_occitanie(session):
    repo = StationRepository(session)
    stations = repo.list_all()
    assert len(stations) >= 4
    names = {s["name"] for s in stations}
    assert any("Montpellier" in n for n in names)


def test_upsert_observation_is_idempotent(session):
    obs_repo = ObservationRepository(session)
    station_repo = StationRepository(session)
    stations = station_repo.list_all()
    station = stations[0]
    payload = {
        "station_id": station["id"],
        "observed_at": datetime(2024, 1, 1, 12, 0, 0),
        "temperature_c": 12.5,
        "humidity_pct": 80,
        "pressure_hpa": 1015.0,
        "wind_speed_ms": 3.2,
        "wind_direction_deg": 180,
        "precipitation_3h_mm": 0.0,
        "precipitation_24h_mm": 0.0,
        "cloud_cover_pct": 50,
        "weather_code": 0,
    }
    obs_repo.upsert(payload)
    obs_repo.upsert(payload)
    session.commit()
    # On récupère assez large car la DB peut déjà contenir des observations
    # ingérées par d'autres sessions ; on cherche l'observation par sa date exacte.
    rows = obs_repo.fetch_for_station(station["id"], limit=100_000)

    # SQLite renvoie observed_at en TEXT, MySQL en datetime
    def _as_dt(v):
        if isinstance(v, datetime):
            return v
        return datetime.fromisoformat(str(v))

    target = payload["observed_at"]
    matching = [r for r in rows if _as_dt(r["observed_at"]) == target]
    assert len(matching) == 1, f"Expected 1 row at {target}, got {len(matching)}"
    assert float(matching[0]["temperature_c"]) == 12.5
