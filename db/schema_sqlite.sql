-- ============================================================
-- Schéma SQLite (variante MVP local — adaptée du schema.sql MySQL)
-- ============================================================
-- Différences vs MySQL :
--   - Pas de PARTITION BY (non supporté par SQLite)
--   - Pas de ENGINE=InnoDB (SQLite n'a pas de moteur de stockage)
--   - Pas de CREATE USER (SQLite est une BDD fichier sans gestion d'utilisateurs)
--   - INTEGER au lieu de BIGINT UNSIGNED / INT UNSIGNED
--   - REAL au lieu de DECIMAL
--   - DATETIME stocké comme TEXT ISO-8601
--
-- Le schéma MySQL d'origine (db/schema.sql) reste la référence pour la prod.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS stations (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  synop_code  TEXT    NOT NULL UNIQUE,
  name        TEXT    NOT NULL,
  department  TEXT,
  latitude    REAL    NOT NULL,
  longitude   REAL    NOT NULL,
  altitude_m  INTEGER,
  region      TEXT    NOT NULL DEFAULT 'Occitanie',
  created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_stations_region ON stations(region);

CREATE TABLE IF NOT EXISTS observations (
  id                    INTEGER PRIMARY KEY AUTOINCREMENT,
  station_id            INTEGER NOT NULL,
  observed_at           TEXT    NOT NULL,
  temperature_c         REAL,
  humidity_pct          INTEGER,
  pressure_hpa          REAL,
  wind_speed_ms         REAL,
  wind_direction_deg    INTEGER,
  precipitation_3h_mm   REAL,
  precipitation_24h_mm  REAL,
  cloud_cover_pct       INTEGER,
  weather_code          INTEGER,
  created_at            TEXT    NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (station_id) REFERENCES stations(id),
  UNIQUE (station_id, observed_at)
);
CREATE INDEX IF NOT EXISTS idx_observations_observed_at ON observations(observed_at);
CREATE INDEX IF NOT EXISTS idx_observations_station_time ON observations(station_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS predictions (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  station_id      INTEGER NOT NULL,
  target_date     TEXT    NOT NULL,
  predicted_proba REAL    NOT NULL,
  predicted_label INTEGER NOT NULL,
  model_version   TEXT    NOT NULL,
  features_hash   TEXT,
  created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (station_id) REFERENCES stations(id)
);
CREATE INDEX IF NOT EXISTS idx_predictions_target_date ON predictions(target_date);
CREATE INDEX IF NOT EXISTS idx_predictions_model_version ON predictions(model_version);

-- Seed stations Occitanie
INSERT OR IGNORE INTO stations (synop_code, name, department, latitude, longitude, altitude_m, region) VALUES
  ('07643', 'Montpellier-Fréjorgues', 'Hérault',             43.576944, 3.963056,   2, 'Occitanie'),
  ('07630', 'Toulouse-Blagnac',       'Haute-Garonne',       43.621389, 1.378889, 151, 'Occitanie'),
  ('07747', 'Perpignan-Rivesaltes',   'Pyrénées-Orientales', 42.737222, 2.872500,  42, 'Occitanie'),
  ('07621', 'Carcassonne-Salvaza',    'Aude',                43.215000, 2.306400, 126, 'Occitanie');
