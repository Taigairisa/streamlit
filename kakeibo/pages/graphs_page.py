import streamlit as st
import pandas as pd
from kakeibo.db import get_monthly_summary


def render():
    st.title("収支推移グラフ")
    monthly_data = get_monthly_summary()

    dates = pd.to_datetime(monthly_data.index)
    start_date = dates.min()
    end_date = dates.max()

    selected_start, selected_end = st.select_slider(
        "表示期間を選択",
        options=dates,
        value=(start_date, end_date),
        format_func=lambda x: x.strftime("%Y-%m"),
    )

    mask = (dates >= selected_start) & (dates <= selected_end)
    filtered_data = monthly_data[mask]

    st.subheader('月次収支（2023年10月以降）')
    st.line_chart(filtered_data[['収入', '支出']])

    st.subheader('累計資産推移（2023年10月以降）')
    st.line_chart(filtered_data[['累計資産']])

    st.write("### 月次データ")
    st.dataframe(filtered_data.style.format('{:,.0f}'))

