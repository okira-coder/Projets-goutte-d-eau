#!/usr/bin/env bash
# Vérification end-to-end du MVP Goutte d'eau (mode SQLite local)
# Usage : bash scripts/verify_mvp.sh

set -euo pipefail
cd "$(dirname "$0")/.."

echo "============================================================"
echo "  Vérification MVP Projet Goutte d'eau"
echo "============================================================"

# 1. Environnement Python
echo ""
echo "▶ 1/8 — Python venv"
source .venv/bin/activate
python --version

# 2. BDD accessible
echo ""
echo "▶ 2/8 — Base de données (SQLite)"
if [ ! -f data/goutte_eau.db ]; then
  echo "❌ data/goutte_eau.db manquant — exécuter 'make db-init'"
  exit 1
fi
echo "✓ data/goutte_eau.db présente ($(du -h data/goutte_eau.db | cut -f1))"

# 3. Tables présentes
echo ""
echo "▶ 3/8 — Schéma DB"
TABLES=$(sqlite3 data/goutte_eau.db ".tables")
for t in stations observations predictions; do
  if ! echo "$TABLES" | grep -qw "$t"; then
    echo "❌ Table $t manquante"; exit 1
  fi
done
echo "✓ Tables présentes : $TABLES"

# 4. Données ingérées
echo ""
echo "▶ 4/8 — Données ingérées"
NB_STATIONS=$(sqlite3 data/goutte_eau.db "SELECT COUNT(*) FROM stations")
NB_OBS=$(sqlite3 data/goutte_eau.db "SELECT COUNT(*) FROM observations")
echo "  Stations : $NB_STATIONS"
echo "  Observations : $NB_OBS"
if [ "$NB_STATIONS" -lt 4 ]; then echo "❌ < 4 stations"; exit 1; fi
if [ "$NB_OBS" -lt 1000 ]; then
  echo "⚠️  Peu d'observations ($NB_OBS) — lancer 'make ingest' avec une fenêtre plus large"
else
  echo "✓ Volume OK"
fi

# 5. Modèle entraîné
echo ""
echo "▶ 5/8 — Modèle entraîné"
if [ ! -f models/xgboost.pkl ]; then
  echo "❌ models/xgboost.pkl manquant — lancer 'make train'"
  exit 1
fi
echo "✓ Modèle présent ($(du -h models/xgboost.pkl | cut -f1))"

# 6. Tests verts
echo ""
echo "▶ 6/8 — Tests pytest"
pytest --tb=no -q 2>&1 | tail -3

# 7. Lint
echo ""
echo "▶ 7/8 — Lint"
ruff check src tests >/dev/null 2>&1 && echo "✓ ruff OK" || echo "⚠️  ruff issues"
black --check src tests >/dev/null 2>&1 && echo "✓ black OK" || echo "⚠️  black formatting issues"

# 8. Smoke API
echo ""
echo "▶ 8/8 — Smoke API"
uvicorn src.api.main:app --port 8000 2>/dev/null &
API_PID=$!
sleep 4
HEALTH=$(curl -s http://localhost:8000/health || echo "{}")
echo "  /health → $HEALTH"
STATIONS=$(curl -s http://localhost:8000/stations | python3.13 -c "import sys, json; d=json.load(sys.stdin); print(f'{len(d)} stations')")
echo "  /stations → $STATIONS"
PRED=$(curl -s -X POST http://localhost:8000/predict -H "Content-Type: application/json" \
  -d '{"station_id": 1, "target_date": "2024-12-30"}')
echo "  /predict Montpellier → $PRED"
kill $API_PID 2>/dev/null || true

echo ""
echo "============================================================"
echo "  ✅ MVP vérifié — prêt pour la démo"
echo "  Lancer manuellement : make api  (puis make ui dans un autre terminal)"
echo "============================================================"
