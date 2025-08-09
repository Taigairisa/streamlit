from datetime import date
import streamlit as st
from sqlalchemy import text
from kakeibo.db import connect_db


def render(main_category_id: int, sub_categories: list):
    sub_category = st.selectbox("サブカテゴリ", [sub[2] for sub in sub_categories if sub[1] == main_category_id])
    sub_category_id = next(sub[0] for sub in sub_categories if sub[2] == sub_category)

    selected_date = st.date_input("日付", value=date.today())
    input_type = st.selectbox("種別", ["支出", "収入", "予算"])
    detail = st.text_input("詳細")
    expense = st.number_input("支出額", min_value=0)

    if st.button("データを追加"):
        engine = connect_db()
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO transactions (sub_category_id, amount, type, date, detail)
                    VALUES (:sid, :amount, :type, :date, :detail)
                    """
                ),
                {
                    "sid": sub_category_id,
                    "amount": expense,
                    "type": input_type,
                    "date": selected_date.strftime("%Y-%m-%d"),
                    "detail": detail,
                },
            )
        st.success("データが追加されました")
