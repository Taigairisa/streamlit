import hmac
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Optional

import streamlit as st
from sqlalchemy import text
from kakeibo.db import connect_db


def _env_bool(val: Optional[str]) -> Optional[bool]:
    if val is None:
        return None
    return str(val).strip().lower() in {"1", "true", "yes", "on"}

def _verify_password(stored: str, provided: str, salt: str = "") -> bool:
    """Verify provided password against stored value.

    Supported formats:
    - plain:<password>
    - sha256:<hex-digest>  (computed as sha256(salt + provided))
    """
    if not isinstance(stored, str):
        return False
    if stored.startswith("plain:"):
        expected = stored.split(":", 1)[1]
        return hmac.compare_digest(expected, provided)
    if stored.startswith("sha256:"):
        # Backward compatibility: if salt provided, use salt+password; else use password only
        expected_hex = stored.split(":", 1)[1]
        base = (salt + provided) if salt else provided
        digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
        return hmac.compare_digest(expected_hex, digest)
    if stored.startswith("pbkdf2_sha256:"):
        try:
            scheme, rest = stored.split(":", 1)
            iters_s, salt_hex, hash_hex = rest.split("$")
            iterations = int(iters_s)
            salt_bytes = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
            dk = hashlib.pbkdf2_hmac("sha256", provided.encode("utf-8"), salt_bytes, iterations)
            return hmac.compare_digest(expected, dk)
        except Exception:
            return False
    # Unsupported scheme
    return False


def _ensure_users_table():
    """Create users table if not exists. Uses a single-column password field in the same
    "scheme:value" format as secrets (e.g., "sha256:<hex>" or "plain:<pwd>").
    """
    engine = connect_db()
    sql = text(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(sql)


def _db_get_user_password(username: str) -> Optional[str]:
    engine = connect_db()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT password FROM users WHERE username = :u"), {"u": username}
        ).fetchone()
    if not row:
        return None
    return row[0]


def _db_user_exists(username: str) -> bool:
    engine = connect_db()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM users WHERE username = :u"), {"u": username}
        ).fetchone()
    return bool(row)


def _db_create_user(username: str, stored_password: str) -> None:
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO users (username, password) VALUES (:u, :p)"),
            {"u": username, "p": stored_password},
        )


def _db_has_any_user() -> bool:
    engine = connect_db()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT 1 FROM users LIMIT 1")).fetchone()
    return bool(row)


def ensure_authenticated() -> Optional[str]:
    """Gate the app until a valid login. Returns the username or None if blocked.

    DB-only authentication. If no user exists yet, encourage registration.
    """
    salt = ""  # Deprecated global salt; kept for backward compatibility with sha256 scheme

    # Logout control in sidebar
    if st.session_state.get("auth_user"):
        with st.sidebar:
            if st.button("ログアウト"):
                st.session_state.pop("auth_user", None)
                st.rerun()

    if st.session_state.get("auth_user"):
        return st.session_state["auth_user"]

    _ensure_users_table()
    st.title("認証")
    tabs = ["ログイン", "新規登録"]
    # If no users yet, open register tab by default to guide first user
    default_index = 1 if not _db_has_any_user() else 0
    tab_login, tab_register = st.tabs(tabs)

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("ユーザー名")
            password = st.text_input("パスワード", type="password")
            submitted = st.form_submit_button("ログイン")

        if submitted:
            ok = False
            stored_db = _db_get_user_password(username)
            if stored_db and _verify_password(stored_db, password, salt=salt):
                ok = True
            if ok:
                st.session_state["auth_user"] = username
                st.success("ログインしました。")
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが正しくありません。")

    with tab_register:
        st.caption("パスワードは安全な方法でハッシュ化して保存します。")
        with st.form("register_form", clear_on_submit=False):
            new_user = st.text_input("ユーザー名（英数字/._- 3〜32文字）")
            new_pass = st.text_input("パスワード", type="password")
            new_pass2 = st.text_input("パスワード（確認）", type="password")
            submitted_reg = st.form_submit_button("登録")

        if submitted_reg:
            # Basic validations
            import re

            if not new_user or not re.fullmatch(r"[A-Za-z0-9._-]{3,32}", new_user):
                st.error("ユーザー名の形式が正しくありません。")
                st.stop()
            if not new_pass or len(new_pass) < 8:
                st.error("パスワードは8文字以上で入力してください。")
                st.stop()
            if new_pass != new_pass2:
                st.error("パスワードが一致しません。")
                st.stop()

            # Check duplicates in secrets or DB
            if _db_user_exists(new_user):
                st.error("このユーザー名は既に登録されています。")
                st.stop()

            # Hash and store using PBKDF2-HMAC-SHA256 with per-user salt
            iterations = 100_000
            salt_bytes = os.urandom(16)
            dk = hashlib.pbkdf2_hmac(
                "sha256", new_pass.encode("utf-8"), salt_bytes, iterations
            )
            stored_fmt = f"pbkdf2_sha256:{iterations}${salt_bytes.hex()}${dk.hex()}"
            try:
                _db_create_user(new_user, stored_fmt)
            except Exception as e:
                st.error("登録に失敗しました。別のユーザー名でお試しください。")
                st.stop()

            st.success("登録が完了しました。ログインします…")
            st.session_state["auth_user"] = new_user
            st.rerun()

    # Block the rest of the page
    st.stop()
    return None
