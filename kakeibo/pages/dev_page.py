import streamlit as st
import pandas as pd
from sqlalchemy import text
from kakeibo.db import DB_FILENAME, connect_db


def render():
    with open(DB_FILENAME, "rb") as file:
        st.download_button(
            label="DBファイルのダウンロード",
            data=file,
            file_name="kakeibo_backup.db",
            mime="application/octet-stream",
        )

    with st.form("SQLクエリ"):
        query = st.text_area("SQLクエリ", "SELECT * FROM transactions")
        if st.form_submit_button("実行"):
            engine = connect_db()
            try:
                if query.strip().upper().startswith("SELECT"):
                    with engine.connect() as conn:
                        df = pd.read_sql(text(query), conn)
                        st.write(df)
                elif any(query.strip().upper().startswith(x) for x in ("INSERT", "UPDATE", "DELETE")):
                    if st.button("本当に実行しますか？"):
                        with engine.begin() as conn:
                            conn.execute(text(query))
                        st.success("クエリを実行しました")
                else:
                    st.warning("SELECT/INSERT/UPDATE/DELETE のいずれかを実行してください")
            except Exception as e:
                st.error(f"Error: {e}")
