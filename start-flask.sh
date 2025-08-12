#!/bin/sh
set -e

# gunicornを絶対パスで起動
/app/.venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 flask_app:app
