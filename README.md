# 🌧️ Projet Goutte d'eau

> **MVP de prévision de pluie pour les agriculteurs d'Occitanie**, basé sur les observations SYNOP de Météo France et un modèle XGBoost de classification binaire à J+1.

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.36+-FF4B4B.svg)](https://streamlit.io/)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.1+-orange.svg)](https://xgboost.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Contexte

France Météo, établissement public national, fait face à des phénomènes pluvieux extrêmes croissants liés au changement climatique. Les modèles actuels de prévision atteignent leurs limites.

Le **Projet Goutte d'eau** vise à refondre les algorithmes de prévision de pluie à destination des **agriculteurs**, en s'appuyant sur l'intelligence artificielle et les flux de données issus de capteurs météorologiques (IoT-ready). Le périmètre du MVP est limité à **une région : l'Occitanie**.

## ✨ Fonctionnalités

- **Collecte automatique** des données SYNOP de Météo France (archives publiques mensuelles)
- **Persistance SQL** dans SQLite (local) ou MySQL (production) — dual-compatible via SQLAlchemy
- **Analyse exploratoire** dans un notebook Jupyter avec démarche *analyse → constat → décision*
- **Modèle ML** XGBoost de classification binaire (pluie significative > 1 mm à J+1)
- **API REST FastAPI** avec documentation OpenAPI auto-générée
- **Interface graphique Streamlit** pour démontrer le fonctionnement
- **Tests automatisés** (33 tests, ~ 64 % de coverage)
- **Validation de bout en bout** via `scripts/verify_mvp.sh`

## 🏗️ Architecture

```
┌─────────────────────────┐
│  👨‍🌾 Agriculteur          │
└───────────┬─────────────┘
            │ HTTP
            ▼
┌─────────────────────────┐
│  Streamlit UI (8501)    │  ← Démonstrateur
└───────────┬─────────────┘
            │ HTTP/JSON
            ▼
┌─────────────────────────┐
│   FastAPI (8000)        │
│   /predict /health      │
│   /stations /docs       │
└─────┬───────────┬───────┘
      │           │
      ▼           ▼
┌──────────┐ ┌──────────────┐
│ BDD SQL  │ │ Modèle .pkl  │
│ SQLite / │ │ XGBoost      │
│ MySQL    │ │ chargé RAM   │
└────▲─────┘ └──────▲───────┘
     │              │
     │       ┌──────┴──────────┐
     │       │ ml_training     │
     │       └──────▲──────────┘
     │              │
     │       ┌──────┴──────────┐
     │       │ build_features  │ ← Single Source of Truth (train + serve)
     │       └──────▲──────────┘
     │              │
     │      ┌───────┴──────────┐
     └──────┤ data_ingestion   │ ← API Météo France SYNOP
            └──────────────────┘
```

**5 composants Python isolés** :

| # | Composant | Responsabilité |
|---|-----------|----------------|
| 1 | `src/ingestion/` | Collecte SYNOP (Météo France) → BDD |
| 2 | `notebooks/01_eda.ipynb` | Analyse exploratoire et choix de modélisation |
| 3 | `src/features/build_features.py` | Feature engineering — *Single Source of Truth* partagée train + serve |
| 4 | `src/models/` | Entraînement (LogReg + XGBoost) + service d'inférence |
| 5 | `src/api/` + `streamlit_app/` | Exposition HTTP + UI démonstrateur |

## 🧰 Stack technique

- **Langage** : Python 3.13
- **Web** : FastAPI 0.115 + Uvicorn (API), Streamlit 1.36 (UI)
- **ORM** : SQLAlchemy 2.0
- **BDD** : SQLite (local) / MySQL 8 (production cible) — dual-compatible
- **ML** : scikit-learn 1.5, XGBoost 2.1, pandas 2.2, NumPy 1.26
- **Validation** : Pydantic 2.7
- **HTTP client** : httpx + tenacity (retries exponentiels)
- **Persistance modèle** : joblib
- **Visualisation** : matplotlib + seaborn (notebooks)
- **Tests** : pytest + pytest-cov
- **Lint/format** : ruff + black

## 🚀 Démarrage rapide

### Pré-requis
- Python 3.13 (`brew install python@3.13` sur macOS)
- libomp pour XGBoost sur macOS (`brew install libomp`)
- sqlite3 (inclus avec macOS)

### Installation

```bash
git clone git@github.com:okira-coder/Projets-goutte-d-eau.git
cd Projets-goutte-d-eau

# Crée le venv et installe les dépendances
make install
```

### Configuration

Copier `.env.example` vers `.env` et adapter si besoin (les valeurs par défaut fonctionnent pour le MVP local SQLite) :

```bash
cp .env.example .env
```

### Pipeline complet

```bash
# 1. Initialiser la BDD SQLite (4 stations Occitanie en seed)
make db-init

# 2. Collecter ~ 2 ans de données SYNOP (≈ 30 secondes)
. .venv/bin/activate && python -m src.ingestion.ingest_job --start 2023-01-01 --end 2024-12-31

# 3. Entraîner les modèles LogReg + XGBoost (≈ 10 secondes)
make train

# 4. Lancer l'API (terminal 1)
make api          # http://localhost:8000/docs

# 5. Lancer l'UI Streamlit (terminal 2)
make ui           # http://localhost:8501
```

### Vérification end-to-end

```bash
bash scripts/verify_mvp.sh
```

Sortie attendue :
```
▶ 1/8 — Python venv → Python 3.13.x ✓
▶ 2/8 — Base de données (SQLite) ✓
▶ 3/8 — Schéma DB → 3 tables ✓
▶ 4/8 — Données ingérées → 4 stations, 23 000+ observations ✓
▶ 5/8 — Modèle entraîné ✓
▶ 6/8 — Tests pytest → 33 passed ✓
▶ 7/8 — Lint → ruff OK, black OK ✓
▶ 8/8 — Smoke API → /health, /stations, /predict ✓
```

## 📊 Stations Occitanie

| Code SYNOP | Nom | Département | Lat | Lon | Altitude |
|-----------|-----|-------------|-----|-----|----------|
| 07643 | Montpellier-Fréjorgues | Hérault | 43.577 | 3.963 | 2 m |
| 07630 | Toulouse-Blagnac | Haute-Garonne | 43.621 | 1.379 | 151 m |
| 07747 | Perpignan-Rivesaltes | Pyrénées-Orientales | 42.737 | 2.873 | 42 m |
| 07621 | Carcassonne-Salvaza | Aude | 43.215 | 2.306 | 126 m |

## 🧠 Modèle

| Aspect | Choix |
|--------|-------|
| **Tâche** | Classification binaire — pluie significative à J+1 (cumul > 1 mm) |
| **Algorithmes** | XGBoost (principal, 300 arbres, max_depth 5) + LogisticRegression (baseline) |
| **Features** | 30+ features structurées en 6 familles (brutes, lags 1-7j, rolling 7/30j, différentielles 24h, saisonnier sin/cos, géographique) |
| **Split** | Temporel 80/20 (pas de shuffle pour éviter la fuite passé → futur) |
| **Validation** | `TimeSeriesSplit(n_splits=5)` |
| **Métriques** | ROC-AUC, F1, Brier score, matrice de confusion, courbe de calibration |
| **Anti-skew** | `build_features.py` est l'unique source de vérité partagée entre entraînement et inférence |

### Performances actuelles (test set, 2 ans de données SYNOP)

| Métrique | LogReg | **XGBoost** |
|----------|--------|-------------|
| ROC-AUC | 0.696 | 0.685 |
| F1 (classe pluie) | 0.426 | 0.300 |
| Brier score | 0.188 | **0.171** |
| CV AUC (TimeSeriesSplit) | — | **0.721 ± 0.058** |

> **Note d'honnêteté** : ces métriques sont **en-dessous de la cible MVP** (ROC-AUC ≥ 0.75), ce qui est attendu pour un modèle exclusivement basé sur SYNOP sans intégration de modèles numériques (AROME/ECMWF). Voir [`reports/model_evaluation.md`](reports/model_evaluation.md) pour l'analyse complète et la roadmap d'amélioration priorisée (P1 à P6).

## 🌐 API

Documentation interactive auto-générée à `http://localhost:8000/docs`.

### Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/` | Métadonnées de l'API |
| `GET` | `/health` | Statut app + DB + modèle |
| `GET` | `/stations` | Liste des stations Occitanie |
| `POST` | `/predict` | Prédiction par `(station_id, target_date)` |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/openapi.json` | Schéma OpenAPI |

### Exemple d'utilisation

```bash
# Lister les stations
curl http://localhost:8000/stations

# Prédire le risque de pluie pour Montpellier
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"station_id": 1, "target_date": "2024-12-30"}'
```

Réponse :
```json
{
  "station_id": 1,
  "station_name": "Montpellier-Fréjorgues",
  "target_date": "2024-12-30",
  "predicted_proba": 0.0208,
  "predicted_label": 0,
  "risk_level": "bas",
  "model_version": "xgb-1.0.0",
  "computed_at": "2026-05-12T08:36:36.013913Z"
}
```

## 🗄️ Schéma de base de données

3 tables principales (voir [`db/schema.sql`](db/schema.sql) pour MySQL ou [`db/schema_sqlite.sql`](db/schema_sqlite.sql) pour SQLite) :

- **`stations`** — référentiel des stations météo (4 stations Occitanie)
- **`observations`** — observations 3h (température, humidité, pression, vent, précipitations) avec clé unique `(station_id, observed_at)` pour idempotence
- **`predictions`** — journal d'audit des prédictions servies (monitoring drift)

## 🧪 Tests

```bash
make test
# ou
. .venv/bin/activate && pytest tests/ -v --cov=src --cov-report=term-missing
```

**33 tests** couvrant :
- Configuration et chargement env
- Client SYNOP (parsing CSV, conversions K°→°C, Pa→hPa, gestion NA)
- Repository DB (upsert idempotent, fetch)
- Feature engineering (lags, rolling, anti-leakage)
- Training (split temporel, métriques)
- Service d'inférence (chargement modèle, hash features)
- API (health, predict, validation Pydantic, OpenAPI)
- Job d'ingestion (génération mois)

## 📁 Structure du projet

```
Projets-goutte-d-eau/
├── README.md
├── LICENSE                  (MIT)
├── Makefile                 (cibles install, ingest, train, api, ui, test, lint, format)
├── pyproject.toml           (dépendances + outils dev)
├── .env.example             (template configuration)
├── .gitignore
│
├── db/                      Schémas SQL + seeds
│   ├── schema.sql           (cible production : MySQL 8 + InnoDB + partitionnement)
│   ├── schema_sqlite.sql    (MVP local : SQLite, drop-in compatible)
│   └── seeds/
│       └── stations_occitanie.sql
│
├── src/                     Code Python (5 composants)
│   ├── config.py            (pydantic-settings, dual MySQL/SQLite)
│   ├── api/                 (FastAPI : main, routes, schemas)
│   ├── db/                  (connection SQLAlchemy + repository pattern)
│   ├── ingestion/           (SYNOP client + bulk ingest job)
│   ├── features/            (build_features.py — SSOT train + serve)
│   └── models/              (train.py, predict.py — ModelService)
│
├── streamlit_app/
│   └── app.py               (UI démonstrateur avec sélecteur station/date)
│
├── notebooks/               (Jupyter, analyse → constat → décision)
│   ├── 01_eda.ipynb         (10 visualisations + synthèse de 6 décisions)
│   └── 03_evaluation.ipynb  (courbe ROC, matrice confusion, calibration, feature importance)
│
├── tests/                   (pytest, 33 tests)
│   ├── unit/                (config, synop_client, build_features, predict)
│   └── integration/         (repository, ingest_job, train, api)
│
├── reports/
│   ├── data_quality_report.md   (sortie EDA, 6 décisions structurantes)
│   ├── model_evaluation.md      (métriques réelles + roadmap d'amélioration)
│   ├── training_summary.json    (snapshot des métriques)
│   └── figures/                 (9 PNG : distributions, séries temporelles, ROC, calibration…)
│
├── models/                  (artefacts .pkl générés par `make train`, ignorés par git)
└── scripts/
    └── verify_mvp.sh        (vérification end-to-end en 8 étapes)
```

## 📚 Sources de données

- **Météo France — Archive SYNOP publique** (licence ouverte) — fichiers mensuels gzippés
  `https://donneespubliques.meteofrance.fr/donnees_libres/Txt/Synop/Archive/synop.YYYYMM.csv.gz`
- **Format** : CSV séparateur `;`, 60 colonnes, mesures toutes les 3 heures
- **Conversions appliquées** : Kelvin → Celsius, Pascals → hPa, `mq` (manquant) → NULL

## 🔁 Bascule SQLite ↔ MySQL

Le code est **dual-compatible** sans refactor :

```bash
# Mode SQLite (par défaut, MVP local)
DB_DIALECT=sqlite python -m src.ingestion.ingest_job

# Mode MySQL (production)
# Renseigner DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME dans .env
DB_DIALECT=mysql make db-init-mysql
DB_DIALECT=mysql python -m src.ingestion.ingest_job
```

Le repository détecte automatiquement le dialecte et bascule entre `ON CONFLICT DO UPDATE` (SQLite) et `ON DUPLICATE KEY UPDATE` (MySQL).

## 🛠️ Cibles `make`

| Cible | Description |
|-------|-------------|
| `make install` | Crée le venv et installe les dépendances |
| `make db-up` | Démarre MySQL (Homebrew) — production |
| `make db-init` | Crée la base SQLite + seeds stations |
| `make db-init-mysql` | Crée la base MySQL + seeds stations |
| `make db-shell` | Ouvre un shell SQLite |
| `make ingest` | Lance l'ingestion (7 derniers jours par défaut) |
| `make train` | Entraîne les modèles |
| `make api` | Démarre l'API FastAPI (port 8000) |
| `make ui` | Démarre l'UI Streamlit (port 8501) |
| `make test` | Lance tous les tests |
| `make lint` | Lint ruff + black --check |
| `make format` | Auto-format ruff + black |
| `make clean` | Nettoie caches et coverage |

## 📜 Licence

MIT — voir [LICENSE](LICENSE).

## 🙏 Crédits

- **Données** : Météo France (archive SYNOP publique, licence ouverte)
- **Formation** : Mastère Management de la Transformation digitale en IA, **Institut Léonard de Vinci** × **Visiplus digital learning**
- **Cas d'étude** : Bloc de compétences 2 — Conception et développement de l'architecture fonctionnelle (C7–C15)

---

*Réalisé dans le cadre d'un projet pédagogique. Les performances du modèle sont volontairement modestes (volume de données limité à 2 ans, SYNOP seul sans NWP) — voir la roadmap d'amélioration dans [`reports/model_evaluation.md`](reports/model_evaluation.md) pour passer en production réelle.*
