import streamlit as st
from sqlalchemy import text
from kakeibo.db import connect_db


def render(main_category_id: int, sub_categories: list):
    engine = connect_db()
    sub_category_options = [sub[2] for sub in sub_categories if sub[1] == main_category_id] + ["新規カテゴリ"]
    selected_sub_category = st.selectbox("小カテゴリを選択", sub_category_options)

    if selected_sub_category == "新規カテゴリ":
        new_sub_category = st.text_input("新しい小カテゴリ名")
        if st.button("小カテゴリを追加"):
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO sub_categories (main_category_id, name) VALUES (:mid, :name)"),
                    {"mid": main_category_id, "name": new_sub_category},
                )
            st.success("小カテゴリが追加されました")
    else:
        new_sub_category_name = st.text_input("リネームする小カテゴリ名", value=selected_sub_category)
        if st.button("小カテゴリをリネーム"):
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "UPDATE sub_categories SET name = :new WHERE main_category_id = :mid AND name = :old"
                    ),
                    {"new": new_sub_category_name, "mid": main_category_id, "old": selected_sub_category},
                )
            st.success("小カテゴリがリネームされました")
