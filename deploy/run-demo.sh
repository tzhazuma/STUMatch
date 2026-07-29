#!/usr/bin/env bash
# SKDMatch — one-click local/LAN demo launcher (no sudo, no docker required if user-space pg/redis exist)
# Usage: bash deploy/run-demo.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== [1/5] Data layer ==="
export PATH=/tmp/usr/pg/bin:/tmp/usr/redis/bin:$PATH
export LD_LIBRARY_PATH=/tmp/usr/pg/lib:${LD_LIBRARY_PATH:-}
if command -v pg_isready >/dev/null 2>&1 && pg_isready -h 127.0.0.1 -p 5432 -U unimatch >/dev/null 2>&1; then
  echo "  PostgreSQL already running"
elif command -v pg_ctl >/dev/null 2>&1 && [ -f /tmp/pgdata/PG_VERSION ]; then
  echo "  Starting PostgreSQL..."
  pg_ctl -D /tmp/pgdata -l /tmp/pg.log -o "-p 5432 -k /tmp -c listen_addresses=localhost" start
  sleep 2
else
  echo "  WARNING: PostgreSQL not found at /tmp/usr/pg. Start it manually or run docker-compose -f infra/docker-compose.yml up -d"
fi
if command -v redis-cli >/dev/null 2>&1 && redis-cli -p 6379 ping 2>/dev/null | grep -q PONG; then
  echo "  Redis already running"
elif command -v redis-server >/dev/null 2>&1; then
  echo "  Starting Redis..."
  redis-server --daemonize yes --port 6379 --dir /tmp --logfile /tmp/redis.log --save "" --appendonly no
  sleep 1
else
  echo "  WARNING: Redis not found. Start it manually or run docker-compose -f infra/docker-compose.yml up -d"
fi

echo "=== [2/5] Backend (0.0.0.0:8001, CORS=*, STORAGE=local) ==="
cd "$ROOT/services/backend"
source .venv/bin/activate
# kill old backend if any
pkill -f "uvicorn unimatch.main:app.*8001" 2>/dev/null || true
sleep 1
STORAGE_PROVIDER=local CORS_ORIGINS='*' nohup uvicorn unimatch.main:app --host 0.0.0.0 --port 8001 > /tmp/backend.log 2>&1 &
echo "  Backend PID=$!"
sleep 3

echo "=== [3/5] Detect LAN IP ==="
LAN=$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -v '^172\.' | grep -v '^$' | head -1)
LAN=${LAN:-127.0.0.1}
echo "  LAN IP: $LAN"

echo "=== [4/5] Build frontend (VITE_API_BASE_URL=http://$LAN:8001) ==="
cd "$ROOT/apps/web"
VITE_API_BASE_URL="http://$LAN:8001" npm run build 2>&1 | tail -5

echo "=== [5/5] Serve frontend (0.0.0.0:4173) ==="
pkill -f "vite preview.*4173" 2>/dev/null || true
sleep 1
nohup npx vite preview --host 0.0.0.0 --port 4173 > /tmp/frontend.log 2>&1 &
echo "  Frontend PID=$!"
sleep 2

echo ""
echo "============================================"
echo "  SKDMatch demo is running!"
echo "  Local:   http://localhost:4173"
echo "  LAN:     http://$LAN:4173"
echo "  Backend: http://$LAN:8001/docs"
echo ""
echo "  Same-LAN devices (phones, other laptops) can access the LAN URL."
echo "  For public/campus-wide access, see deploy/README_DEPLOY.md"
echo "============================================"
