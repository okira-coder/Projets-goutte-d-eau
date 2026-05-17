-- ============================================================
-- Schéma BDD Projet Goutte d'eau
-- Base : goutte_eau / Charset : utf8mb4 / Moteur : InnoDB
-- ============================================================

DROP DATABASE IF EXISTS goutte_eau;
CREATE DATABASE goutte_eau CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE goutte_eau;

-- Utilisateur applicatif (droits limités, pas de DROP/CREATE)
CREATE USER IF NOT EXISTS 'goutte_app'@'localhost' IDENTIFIED BY 'change_me';
GRANT SELECT, INSERT, UPDATE, DELETE ON goutte_eau.* TO 'goutte_app'@'localhost';
FLUSH PRIVILEGES;

-- ============================================================
-- Table 1 : Stations météo d'Occitanie
-- ============================================================
CREATE TABLE stations (
  id              INT UNSIGNED   AUTO_INCREMENT PRIMARY KEY,
  synop_code      CHAR(5)        NOT NULL UNIQUE COMMENT 'Code SYNOP 5 chiffres',
  name            VARCHAR(100)   NOT NULL,
  department      VARCHAR(50)    NULL,
  latitude        DECIMAL(9,6)   NOT NULL,
  longitude       DECIMAL(9,6)   NOT NULL,
  altitude_m      SMALLINT       NULL,
  region          VARCHAR(50)    NOT NULL DEFAULT 'Occitanie',
  created_at      TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_region (region)
) ENGINE=InnoDB;

-- ============================================================
-- Table 2 : Observations météo (cœur des données)
-- ============================================================
CREATE TABLE observations (
  id                   BIGINT UNSIGNED AUTO_INCREMENT,
  station_id           INT UNSIGNED    NOT NULL,
  observed_at          DATETIME        NOT NULL COMMENT 'Heure UTC de la mesure',
  -- Mesures atmosphériques
  temperature_c        DECIMAL(4,1)    NULL,
  humidity_pct         TINYINT UNSIGNED NULL,
  pressure_hpa         DECIMAL(6,1)    NULL,
  wind_speed_ms        DECIMAL(4,1)    NULL,
  wind_direction_deg   SMALLINT        NULL,
  -- Précipitations
  precipitation_3h_mm  DECIMAL(5,1)    NULL COMMENT 'Cumul 3h en mm',
  precipitation_24h_mm DECIMAL(5,1)    NULL,
  -- Méta
  cloud_cover_pct      TINYINT UNSIGNED NULL,
  weather_code         SMALLINT        NULL COMMENT 'Code WMO temps présent',
  created_at           TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (id, observed_at),
  CONSTRAINT fk_obs_station FOREIGN KEY (station_id) REFERENCES stations(id),
  UNIQUE KEY uq_station_time (station_id, observed_at),
  INDEX idx_observed_at (observed_at),
  INDEX idx_station_time (station_id, observed_at DESC)
) ENGINE=InnoDB
  PARTITION BY RANGE (YEAR(observed_at)) (
    PARTITION p2022 VALUES LESS THAN (2023),
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p2026 VALUES LESS THAN (2027),
    PARTITION pmax  VALUES LESS THAN MAXVALUE
  );

-- ============================================================
-- Table 3 : Journal des prédictions (audit + monitoring)
-- ============================================================
CREATE TABLE predictions (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  station_id      INT UNSIGNED    NOT NULL,
  target_date     DATE            NOT NULL,
  predicted_proba DECIMAL(5,4)    NOT NULL COMMENT 'P(pluie) entre 0 et 1',
  predicted_label TINYINT         NOT NULL COMMENT '0 = pas de pluie, 1 = pluie',
  model_version   VARCHAR(20)     NOT NULL,
  features_hash   CHAR(64)        NULL COMMENT 'SHA-256 vecteur features',
  created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_pred_station FOREIGN KEY (station_id) REFERENCES stations(id),
  INDEX idx_target_date (target_date),
  INDEX idx_model_version (model_version)
) ENGINE=InnoDB;
