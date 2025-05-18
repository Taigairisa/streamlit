"""
Single‑file Streamlit Chatbot (OpenAI v1 compatible)
===================================================
Run:
    streamlit run Chatbot.py

Install once:
    pip install streamlit openai  # openai>=1.3.0 推奨

Secrets:
    Streamlit Cloud → Settings → Secrets で
    OPENAI_API_KEY="sk‑..."

ローカルなら:
    export OPENAI_API_KEY="sk‑..."  # Windows は set
"""
from __future__ import annotations
import os
import sys
import streamlit as st

# -----------------------------------------------------------------------------
# 0.  OpenAI キー
# -----------------------------------------------------------------------------
OPENAI_API_KEY: str | None = (
    st.secrets.get("OPENAI_API_KEY")  # Cloud
    or os.getenv("OPENAI_API_KEY")    # Local
)
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY が見つからへんで！Secrets か環境変数にセットしてな。")
    st.stop()

# -----------------------------------------------------------------------------
# 1.  openai ライブラリとの互換層
# -----------------------------------------------------------------------------
try:
    # openai>=1.0 では OpenAI クラス経由
    from openai import OpenAI  # type: ignore

    _client = OpenAI(api_key=OPENAI_API_KEY)

    def stream_chat_completion(messages: list[dict]) -> object:  # returns generator
        return _client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            stream=True,
        )

except ImportError:  # fall back to <1.0 interface
    import openai  # type: ignore

    if tuple(map(int, openai.__version__.split("."))) >= (1, 0):
        st.exception(
            RuntimeError(
                "openai>=1.0 が入っているのに ImportError が出た場合は依存関係の競合かも。\n"
                "\n対処: `pip install --upgrade --no‑cache‑dir openai streamlit` で再インストールするか、\n"
                "旧 API を使いたいなら `pip install openai==0.28` に固定してや。"
            )
        )
        st.stop()

    openai.api_key = OPENAI_API_KEY

    def stream_chat_completion(messages: list[dict]) -> object:
        return openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            stream=True,
        )

# -----------------------------------------------------------------------------
# 2.  ページ設定
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Chatbot", page_icon="🤖", initial_sidebar_state="collapsed")
st.title("🤖 Chatbot (Streamlit × OpenAI)")

# -----------------------------------------------------------------------------
# 3.  チャット履歴の初期化
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages: list[dict] = [
        {"role": "assistant", "content": "こんにちは！なんでも聞いてや〜"}
    ]

# -----------------------------------------------------------------------------
# 4.  これまでのメッセージを表示
# -----------------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -----------------------------------------------------------------------------
# 5.  ユーザー入力
# -----------------------------------------------------------------------------
if prompt := st.chat_input("メッセージを入力してや〜"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # -------------------------------------------------------------------------
    # 6.  OpenAI へ問い合わせ（ストリーミング表示）
    # -------------------------------------------------------------------------
    try:
        response = stream_chat_completion(st.session_state.messages)
    except Exception as e:
        st.error(f"OpenAI API 呼び出しでエラー: {e}")
        st.stop()

    full_reply = ""
    with st.chat_message("assistant"):
        placeholder = st.empty()
        for chunk in response:
            # openai>=1.0 と <1.0 で JSON 形が違うので両対応
            delta = (
                chunk.choices[0].delta  # >=1.0 (pydantic obj)
                if hasattr(chunk.choices[0], "delta")
                else chunk.choices[0].delta  # type: ignore[attr-defined]
            )
            content = getattr(delta, "content", None) or delta.get("content")
            if content:
                full_reply += content
                placeholder.markdown(full_reply + "▌")
        placeholder.markdown(full_reply)

    st.session_state.messages.append({"role": "assistant", "content": full_reply})

# -----------------------------------------------------------------------------
# 7.  フッター
# -----------------------------------------------------------------------------
st.markdown("---")
st.caption("Made with ❤️ & Streamlit")
