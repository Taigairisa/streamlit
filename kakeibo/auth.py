import hmac
import hashlib
import os
from typing import Optional

import streamlit as st
from sqlalchemy import text
from kakeibo.db import connect_db
from .line_auth import line_login_flow, _get_line_config


def _verify_password(stored: str, provided: str, salt: str = "") -> bool:
    if not isinstance(stored, str):
        return False
    if stored.startswith("plain:"):
        expected = stored.split(":", 1)[1]
        return hmac.compare_digest(expected, provided)
    if stored.startswith("sha256:"):
        expected_hex = stored.split(":", 1)[1]
        base = (salt + provided) if salt else provided
        digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
        return hmac.compare_digest(expected_hex, digest)
    if stored.startswith("pbkdf2_sha256:"):
        try:
            _, rest = stored.split(":", 1)
            iters_s, salt_hex, hash_hex = rest.split("$")
            iterations = int(iters_s)
            salt_bytes = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
            dk = hashlib.pbkdf2_hmac("sha256", provided.encode("utf-8"), salt_bytes, iterations)
            return hmac.compare_digest(expected, dk)
        except Exception:
            return False
    return False


def _ensure_users_table():
    engine = connect_db()
    sql = text("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    with engine.begin() as conn:
        conn.execute(sql)


def _db_get_user_password(username: str) -> Optional[str]:
    engine = connect_db()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT password FROM users WHERE username = :u"), {"u": username}).fetchone()
    return row[0] if row else None


def _db_user_exists(username: str) -> bool:
    engine = connect_db()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT 1 FROM users WHERE username = :u"), {"u": username}).fetchone()
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

def _do_logout():
    # 1) URLクエリを確実に消す
    try:
        st.query_params.clear()
    except Exception:
        # 古いStreamlit互換
        st.experimental_set_query_params()

    # 2) セッションをまるごと初期化（auth関連含む）
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    # 3) 念のためのフラグ（メッセージ出すなら使える）
    st.session_state["just_logged_out"] = True


def ensure_authenticated() -> Optional[str]:
    """
    ログイン済みユーザー名を返す。未ログインならUIでブロック。
    LINEログイン（DB-backed state）＋ 従来のユーザー名/パスワードの併用。
    """
    salt = ""

    # すでにログイン済みなら、クエリ(code/state)が付いていても掃除しておく
    if st.session_state.get("auth_user"):
        if "code" in st.query_params or "state" in st.query_params:
            try:
                st.query_params.clear()
            except Exception:
                st.experimental_set_query_params()
            st.rerun()


    # ログアウトボタン（必ずクエリを掃除）
    if st.session_state.get("auth_user"):
        with st.sidebar:
            if st.session_state.get("auth_user"):
                st.button("ログアウト", key="logout_btn", on_click=_do_logout)  # ← これがミソ     # ← これだけ

    if st.session_state.get("auth_user"):
        return st.session_state["auth_user"]

    _ensure_users_table()
    st.title("認証")
    tabs = ["LINEでログイン", "ユーザー名でログイン", "新規登録"]
    tab_line, tab_login, tab_register = st.tabs(tabs)

    # ---- LINEログイン ----
    with tab_line:
        cfg = _get_line_config()
        if not cfg:
            st.info("LINEログインは未設定です。環境変数 LINE_CLIENT_ID/SECRET/REDIRECT_URI または secrets.toml の [line] を設定してください。")
        else:
            st.caption("LINEアカウントでログインします。初回はLINEの同意画面が表示されます。")
            profile = line_login_flow()
            if profile:  # 成功時のみ返る
                user_id = profile.get("userId")
                display_name = profile.get("displayName")
                if user_id:
                    st.session_state["auth_user"] = f"line:{user_id}"          # ← 重要（URLのcode/stateを消す）
                    st.success(f"{display_name or 'LINEユーザー'}としてログインしました。")
                    st.session_state["auth_user"] = f"line:{user_id}"
                    try:
                        st.query_params.clear()
                    except Exception:
                        st.experimental_set_query_params()
                    st.rerun()


    # ---- ユーザー名/パスワード ----
    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("ユーザー名")
            password = st.text_input("パスワード", type="password")
            submitted = st.form_submit_button("ログイン")
        if submitted:
            stored_db = _db_get_user_password(username)
            ok = bool(stored_db and _verify_password(stored_db, password, salt=salt))
            if ok:
                st.session_state["auth_user"] = username
                st.query_params.clear()                 # 万一クエリが残っていても掃除
                st.success("ログインしました。")
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが正しくありません。")

    # ---- 新規登録 ----
    with tab_register:
        st.caption("パスワードは安全な方法でハッシュ化して保存します。")
        with st.form("register_form", clear_on_submit=False):
            new_user = st.text_input("ユーザー名（英数字/._- 3〜32文字）")
            new_pass = st.text_input("パスワード", type="password")
            new_pass2 = st.text_input("パスワード（確認）", type="password")
            submitted_reg = st.form_submit_button("登録")

        if submitted_reg:
            import re
            if not new_user or not re.fullmatch(r"[A-Za-z0-9._-]{3,32}", new_user):
                st.error("ユーザー名の形式が正しくありません。"); st.stop()
            if not new_pass or len(new_pass) < 8:
                st.error("パスワードは8文字以上で入力してください。"); st.stop()
            if new_pass != new_pass2:
                st.error("パスワードが一致しません。"); st.stop()
            if _db_user_exists(new_user):
                st.error("このユーザー名は既に登録されています。"); st.stop()

            iterations = 100_000
            salt_bytes = os.urandom(16)
            dk = hashlib.pbkdf2_hmac("sha256", new_pass.encode("utf-8"), salt_bytes, iterations)
            stored_fmt = f"pbkdf2_sha256:{iterations}${salt_bytes.hex()}${dk.hex()}"
            try:
                _db_create_user(new_user, stored_fmt)
            except Exception:
                st.error("登録に失敗しました。別のユーザー名でお試しください。"); st.stop()

            st.success("登録が完了しました。ログインします…")
            st.session_state["auth_user"] = new_user
            st.query_params.clear()
            st.rerun()

    st.stop()
    return None
