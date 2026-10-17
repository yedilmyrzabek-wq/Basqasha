#!/usr/bin/env bash
# One-command dev start (macOS/Linux): backend API + Huey worker + frontend (if present).
# Usage: ./scripts/dev.sh   (Ctrl+C stops everything)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/data/logs"

env_value() {  # env_value NAME DEFAULT  (reads ../.env, strips inline comments)
  local v
  v="$(grep -E "^\s*$1\s*=" "$ROOT/.env" 2>/dev/null | head -1 | cut -d= -f2- | sed 's/#.*//' | xargs || true)"
  echo "${v:-$2}"
}
API_HOST="$(env_value BACKEND_HOST 127.0.0.1)"
API_PORT="$(env_value BACKEND_PORT 8000)"

echo "Syncing backend dependencies (uv)..."
(cd "$ROOT/backend" && uv sync --quiet)

pids=()
cleanup() {
  trap - INT TERM EXIT
  for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done
  wait 2>/dev/null || true
  echo "Stopped."
}
trap cleanup INT TERM EXIT

(cd "$ROOT/backend" && exec uv run uvicorn app.main:app --host "$API_HOST" --port "$API_PORT" \
  --reload --reload-dir app --reload-dir ai) & pids+=($!)
# worker restarts on code changes too (a step interrupted by a restart is marked failed -> retry)
(cd "$ROOT/backend" && exec uv run watchfiles --filter python app.worker.main app ai) & pids+=($!)
FRONT_PORT="$(env_value FRONTEND_PORT 5173)"
if (exec 3<>"/dev/tcp/127.0.0.1/$FRONT_PORT") 2>/dev/null; then
  echo "Port $FRONT_PORT is already in use - assuming the frontend dev server is running; not starting another"
elif [ -f "$ROOT/frontend/package.json" ]; then
  [ -d "$ROOT/frontend/node_modules" ] || (cd "$ROOT/frontend" && npm install)
  (cd "$ROOT/frontend" && exec npm run dev -- --port "$FRONT_PORT" --strictPort) & pids+=($!)
else
  echo "frontend/ not found - starting backend only"
fi

echo
echo "API:      http://$API_HOST:$API_PORT/docs"
echo "Frontend: http://localhost:$FRONT_PORT"
echo "Ctrl+C to stop."
wait -n
