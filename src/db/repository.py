from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.config import settings


class StationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[dict[str, Any]]:
        rows = self.session.execute(text("""SELECT id, synop_code, name, department,
                              latitude, longitude, altitude_m, region
                       FROM stations
                       ORDER BY name""")).mappings().all()
        return [dict(r) for r in rows]

    def get_by_synop(self, synop_code: str) -> dict[str, Any] | None:
        r = (
            self.session.execute(
                text("SELECT id, synop_code, name FROM stations WHERE synop_code = :c"),
                {"c": synop_code},
            )
            .mappings()
            .first()
        )
        return dict(r) if r else None


class ObservationRepository:
    # Syntaxe UPSERT dépendante du dialecte
    _MYSQL_UPSERT = text("""
        INSERT INTO observations
          (station_id, observed_at, temperature_c, humidity_pct, pressure_hpa,
           wind_speed_ms, wind_direction_deg, precipitation_3h_mm,
           precipitation_24h_mm, cloud_cover_pct, weather_code)
        VALUES
          (:station_id, :observed_at, :temperature_c, :humidity_pct, :pressure_hpa,
           :wind_speed_ms, :wind_direction_deg, :precipitation_3h_mm,
           :precipitation_24h_mm, :cloud_cover_pct, :weather_code)
        ON DUPLICATE KEY UPDATE
          temperature_c = VALUES(temperature_c),
          humidity_pct = VALUES(humidity_pct),
          pressure_hpa = VALUES(pressure_hpa),
          wind_speed_ms = VALUES(wind_speed_ms),
          wind_direction_deg = VALUES(wind_direction_deg),
          precipitation_3h_mm = VALUES(precipitation_3h_mm),
          precipitation_24h_mm = VALUES(precipitation_24h_mm),
          cloud_cover_pct = VALUES(cloud_cover_pct),
          weather_code = VALUES(weather_code)
        """)
    _SQLITE_UPSERT = text("""
        INSERT INTO observations
          (station_id, observed_at, temperature_c, humidity_pct, pressure_hpa,
           wind_speed_ms, wind_direction_deg, precipitation_3h_mm,
           precipitation_24h_mm, cloud_cover_pct, weather_code)
        VALUES
          (:station_id, :observed_at, :temperature_c, :humidity_pct, :pressure_hpa,
           :wind_speed_ms, :wind_direction_deg, :precipitation_3h_mm,
           :precipitation_24h_mm, :cloud_cover_pct, :weather_code)
        ON CONFLICT(station_id, observed_at) DO UPDATE SET
          temperature_c = excluded.temperature_c,
          humidity_pct = excluded.humidity_pct,
          pressure_hpa = excluded.pressure_hpa,
          wind_speed_ms = excluded.wind_speed_ms,
          wind_direction_deg = excluded.wind_direction_deg,
          precipitation_3h_mm = excluded.precipitation_3h_mm,
          precipitation_24h_mm = excluded.precipitation_24h_mm,
          cloud_cover_pct = excluded.cloud_cover_pct,
          weather_code = excluded.weather_code
        """)

    UPSERT_SQL = _SQLITE_UPSERT if settings.db_dialect == "sqlite" else _MYSQL_UPSERT

    REQUIRED_KEYS = (
        "station_id",
        "observed_at",
        "temperature_c",
        "humidity_pct",
        "pressure_hpa",
        "wind_speed_ms",
        "wind_direction_deg",
        "precipitation_3h_mm",
        "precipitation_24h_mm",
        "cloud_cover_pct",
        "weather_code",
    )

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, payload: dict[str, Any]) -> None:
        params = {k: payload.get(k) for k in self.REQUIRED_KEYS}
        self.session.execute(self.UPSERT_SQL, params)

    def upsert_many(self, payloads: list[dict[str, Any]]) -> int:
        for p in payloads:
            self.upsert(p)
        return len(payloads)

    def fetch_for_station(self, station_id: int, limit: int = 1000) -> list[dict[str, Any]]:
        rows = (
            self.session.execute(
                text("""SELECT station_id, observed_at, temperature_c, humidity_pct,
                              pressure_hpa, wind_speed_ms, wind_direction_deg,
                              precipitation_3h_mm, precipitation_24h_mm,
                              cloud_cover_pct, weather_code
                       FROM observations
                       WHERE station_id = :sid
                       ORDER BY observed_at DESC
                       LIMIT :lim"""),
                {"sid": station_id, "lim": limit},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def count(self) -> int:
        return int(
            self.session.execute(text("SELECT COUNT(*) AS c FROM observations")).scalar_one()
        )
