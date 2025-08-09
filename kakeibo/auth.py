import hmac
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Optional

import streamlit as st


def _env_bool(val: Optional[str]) -> Optional[bool]:
    if val is None:
        return None
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _load_from_env() -> Optional[Dict]:
    """Optional env fallback.

    AUTH_ENABLED=true|false
    AUTH_SALT=...
    AUTH_USERS_JSON='{"user":"plain:pass", "admin":"sha256:..."}'
    """
    enabled = _env_bool(os.environ.get("AUTH_ENABLED"))
    users_json = os.environ.get("AUTH_USERS_JSON")
    salt = os.environ.get("AUTH_SALT")
    if enabled is None and users_json is None and salt is None:
        return None
    users: Dict[str, str] = {}
    if users_json:
        try:
            data = json.loads(users_json)
            if isinstance(data, dict):
                users = {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
    return {"enabled": bool(enabled), "salt": salt or "", "users": users}


def _secrets_file_exists() -> bool:
    # Avoid touching st.secrets if there is no file to prevent noisy warnings
    paths = [
        Path("/app/.streamlit/secrets.toml"),
        Path.home() / ".streamlit" / "secrets.toml",
    ]
    return any(p.exists() for p in paths)


def _get_auth_config() -> Dict:
    """Load auth config from env or Streamlit secrets if present.

    Expected structure in .streamlit/secrets.toml:

    [auth]
    enabled = true
    salt = "change-me"
    [auth.users]
    admin = "sha256:<hex>"
    viewer = "plain:password"
    """
    env_cfg = _load_from_env()
    if env_cfg is not None:
        return env_cfg
    if _secrets_file_exists():
        # Accessing st.secrets only when we know a file exists avoids warnings
        return st.secrets.get("auth", {})
    return {}


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
        expected_hex = stored.split(":", 1)[1]
        digest = hashlib.sha256((salt + provided).encode("utf-8")).hexdigest()
        return hmac.compare_digest(expected_hex, digest)
    # Unsupported scheme
    return False


def ensure_authenticated() -> Optional[str]:
    """Gate the app until a valid login. Returns the username or None if blocked.

    If auth.enabled is false or missing, no gating is applied (returns "anonymous").
    """
    cfg = _get_auth_config()
    enabled = bool(cfg.get("enabled"))
    users: Dict[str, str] = cfg.get("users", {}) or {}
    salt = str(cfg.get("salt", ""))

    # If disabled or no users configured, do not block usage
    if not enabled or not users:
        return "anonymous"

    # Logout control in sidebar
    if st.session_state.get("auth_user"):
        with st.sidebar:
            if st.button("ログアウト"):
                st.session_state.pop("auth_user", None)
                st.rerun()

    if st.session_state.get("auth_user"):
        return st.session_state["auth_user"]

    st.title("ログイン")
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("ユーザー名")
        password = st.text_input("パスワード", type="password")
        submitted = st.form_submit_button("ログイン")

    if submitted:
        stored = users.get(username)
        if stored and _verify_password(stored, password, salt=salt):
            st.session_state["auth_user"] = username
            st.success("ログインしました。")
            st.rerun()
        else:
            st.error("ユーザー名またはパスワードが正しくありません。")

    # Block the rest of the page
    st.stop()
    return None
