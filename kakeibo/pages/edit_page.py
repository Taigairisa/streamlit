from datetime import datetime
import streamlit as st
from kakeibo.db import load_data, update_data


def render(main_category_id: int, sub_categories: list):
    sub_category = st.selectbox("サブカテゴリ", [sub[2] for sub in sub_categories if sub[1] == main_category_id])
    sub_category_id = next(sub[0] for sub in sub_categories if sub[2] == sub_category)
    df = load_data(sub_category_id)
    if df is None or df.empty:
        st.warning("表示するデータがありません")
        st.stop()

    min_date = datetime.strptime(df['date'].min(), "%Y-%m-%d")
    max_date = datetime.strptime(df['date'].max(), "%Y-%m-%d")
    if min_date < max_date:
        start_date, end_date = st.slider(
            "期間を選択",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="YYYY-MM-DD",
        )
    else:
        start_date = end_date = min_date

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("開始日", start_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("終了日", end_date, min_value=min_date, max_value=max_date)

    df = df[(df['date'] >= start_date.strftime("%Y-%m-%d")) & (df['date'] <= end_date.strftime("%Y-%m-%d"))]
    df = df.reset_index(drop=True)

    can_edit_num_rows = "dynamic" if st.toggle("データを追加する") else "fixed"
    st.data_editor(
        df.drop(columns=["sub_category_id"]),
        disabled=["id"],
        num_rows=can_edit_num_rows,
        column_config={
            "amount": st.column_config.NumberColumn(format="¥%f"),
        },
        key="inventory_table",
    )

    has_uncommitted_changes = any(len(v) for v in st.session_state.inventory_table.values())

    total_spent = df[df['type'] == '支出']['amount'].sum()
    total_budget = df[df['type'] == '予算']['amount'].sum()
    st.write(f"合計支出額: {total_spent}円")
    st.write(f"合計予算額: {total_budget}円")

    st.button(
        "Commit changes",
        type="primary",
        disabled=not has_uncommitted_changes,
        on_click=update_data,
        args=(df, st.session_state.inventory_table),
    )
