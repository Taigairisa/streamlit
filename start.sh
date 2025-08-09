#!/bin/sh
set -e

mkdir -p /data

# /data に DB が無ければ seed をコピー（あれば何もしない）
if [ ! -s /data/kakeibo.db ]; then
  if [ -f /app/data/kakeibo.db ]; then
    cp -f /app/data/kakeibo.db /data/kakeibo.db
    echo "Seed DB copied to /data"
  else
    echo "No seed DB found; creating empty schema"
    python - <<'PY'
import sqlite3
db='/data/kakeibo.db'
con=sqlite3.connect(db)
con.executescript("""
CREATE TABLE IF NOT EXISTS main_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sub_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, main_category_id INTEGER NOT NULL, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sub_category_id INTEGER NOT NULL,
  amount INTEGER NOT NULL,
  type TEXT CHECK(type IN ('支出','収入','予算')) NOT NULL,
  date TEXT NOT NULL,
  detail TEXT
);
CREATE TABLE IF NOT EXISTS backup_time (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL);
""")
con.close()
PY
  fi
fi

# Streamlit 起動
exec uv run streamlit run app.py --server.port 8501 --server.address 0.0.0.0
