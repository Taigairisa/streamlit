#!/bin/sh
set -e

# Ensure seeded DB exists in the mounted volume on first run
if [ ! -f "/data/kakeibo.db" ] && [ -f "/app/data/kakeibo.db" ]; then
  mkdir -p /data
  cp /app/data/kakeibo.db /data/kakeibo.db
fi

# gunicornを絶対パスで起動（メモリ節約のためワーカー数を抑制）
WORKERS=${WEB_CONCURRENCY:-1}
THREADS=${GUNICORN_THREADS:-1}
/app/.venv/bin/gunicorn \
  --bind 0.0.0.0:5000 \
  --workers "$WORKERS" \
  --threads "$THREADS" \
  --max-requests 200 \
  --max-requests-jitter 50 \
  --timeout 60 \
  flask_app:app
