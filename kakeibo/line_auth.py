import os
import secrets
import urllib.parse
from typing import Dict, Optional

import requests
import streamlit as st
from sqlalchemy import text
from kakeibo.db import connect_db

LINE_AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
LINE_TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
LINE_PROFILE_URL = "https://api.line.me/v2/profile"


# ---------------------------
# Config
# ---------------------------
def _get_line_config() -> Optional[Dict[str, str]]:
    cid = os.environ.get("LINE_CLIENT_ID")
    csec = os.environ.get("LINE_CLIENT_SECRET")
    redirect = os.environ.get("LINE_REDIRECT_URI")
    if cid and csec and redirect:
        return {"client_id": cid, "client_secret": csec, "redirect_uri": redirect}

    try:
        cfg = st.secrets.get("line", {})
        if cfg and all(k in cfg for k in ("client_id", "client_secret")):
            redirect = cfg.get("redirect_uri") or redirect
            if not redirect:
                redirect = "http://localhost:8501"  # dev fallback
            return {
                "client_id": str(cfg["client_id"]),
                "client_secret": str(cfg["client_secret"]),
                "redirect_uri": redirect,
            }
    except Exception:
        pass
    return None


# ---------------------------
# DB: oauth_states (state一時保存)
# ---------------------------
def _init_state_table():
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """))


def _save_state(state: str):
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO oauth_states (state) VALUES (:s)"), {"s": state})


def _is_valid_state(state: str) -> bool:
    engine = connect_db()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT 1
            FROM oauth_states
            WHERE state = :s
              AND datetime(created_at) >= datetime('now','-10 minutes')
        """), {"s": state}).fetchone()
    return bool(row)


def _remove_state(state: str):
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM oauth_states WHERE state = :s"), {"s": state})


def _cleanup_old_states():
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM oauth_states WHERE datetime(created_at) < datetime('now','-1 day')"
        ))


# ---------------------------
# DB: users（未登録なら作成）
# ---------------------------
def _ensure_users_table():
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """))


def _user_exists(username: str) -> bool:
    engine = connect_db()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT 1 FROM users WHERE username = :u"), {"u": username}).fetchone()
    return bool(row)


def _create_user(username: str):
    # 外部IdPで認証するためダミーパスワードを格納
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO users (username, password) VALUES (:u, :p)"),
            {"u": username, "p": "external"}
        )


# ---------------------------
# Main Flow
# ---------------------------
def line_login_flow() -> Optional[Dict]:
    """
    LINEログイン（OAuth）をDB-backed stateで実施し、成功時はプロフィール(dict)を返す。
    副作用: 認証成功後、usersに「line:<userId>」が未登録なら自動追加。
    """
    cfg = _get_line_config()
    if not cfg:
        st.error("LINEログイン設定が見つかりません。環境変数またはsecrets.tomlを確認してください。")
        return None

    _init_state_table()
    _ensure_users_table()
    _cleanup_old_states()

    qp = st.query_params
    code = qp.get("code")
    state_from_url = qp.get("state")

    # 認証前：state生成→DB保存→LINEへ
    if code is None:
        state = secrets.token_urlsafe(16)
        _save_state(state)

        params = {
            "response_type": "code",
            "client_id": cfg["client_id"],
            "redirect_uri": cfg["redirect_uri"],
            "state": state,
            "scope": "profile openid",
        }
        auth_url = f"{LINE_AUTH_URL}?{urllib.parse.urlencode(params, safe=':/')}"
        st.link_button("LINEでログイン", auth_url)
        st.stop()

    # 認証後：state検証（DB照合 & ワンタイム消費）
    if not state_from_url or not _is_valid_state(state_from_url):
        st.error("不正なリクエスト（state不一致/期限切れ/未登録）。もう一度お試しください。")
        st.stop()
    _remove_state(state_from_url)

    # トークン交換
    token_resp = requests.post(
        LINE_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": cfg["redirect_uri"],
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
        },
        timeout=15,
    )
    if token_resp.status_code != 200:
        st.error("LINEログインに失敗しました。")
        st.stop()

    token_json = token_resp.json()
    access_token = token_json.get("access_token")
    if not access_token:
        st.error("アクセストークンの取得に失敗しました。")
        st.stop()

    # プロフィール取得
    prof_resp = requests.get(
        LINE_PROFILE_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if prof_resp.status_code != 200:
        st.error("ユーザープロフィールの取得に失敗しました。")
        st.stop()

    profile = prof_resp.json()

    # usersに未登録なら追加
    username = f"line:{profile.get('userId')}"
    if username and not _user_exists(username):
        _create_user(username)

    return profile
