#!/usr/bin/env bash
set -uo pipefail

ROOT="/Users/corin44/Dev/lol-predictor"
FRONT="$ROOT/frontend"
API_LOG="/tmp/lol-api.log"
FRONT_LOG="/tmp/lol-frontend.log"

cd "$ROOT"

# Arret des process residuels
pkill -f "uvicorn api.main" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "next start" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
sleep 1

# Verification de la cle API
if ! grep -q "^RIOT_API_KEY=RGAPI-" .env; then
  echo "Erreur : RIOT_API_KEY absente ou invalide dans .env"
  exit 1
fi

# Backend
nohup ./venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 > "$API_LOG" 2>&1 &
echo "API demarree (PID $!) -> $API_LOG"

# Frontend en mode production (stable, faible RAM)
cd "$FRONT"
if [ ! -d ".next" ] || [ "${1:-}" = "--build" ]; then
  echo "Build du frontend..."
  npm run build
fi
nohup npm run start > "$FRONT_LOG" 2>&1 &
echo "Frontend demarre (PID $!) -> $FRONT_LOG"

# Attente de disponibilite
curl -s --retry 40 --retry-connrefused --retry-delay 1 -o /dev/null -w "API      : HTTP %{http_code}\n" http://localhost:8000/docs || true
curl -s --retry 40 --retry-connrefused --retry-delay 1 -o /dev/null -w "Frontend : HTTP %{http_code}\n" http://localhost:3000 || true

echo ""
echo "API      : http://localhost:8000  (docs : /docs)"
echo "Frontend : http://localhost:3000"
