# ./Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Tokyo

# pandas/gspread 等で必要な最低限ツール
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates tzdata \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# uv を使う（ローカルと同じ解決系）
RUN pip install --no-cache-dir uv

# 依存ファイル → 先にコピーしてキャッシュ活用
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen || uv sync

# アプリ本体
COPY . .

# Streamlit を外から叩けるように
EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
