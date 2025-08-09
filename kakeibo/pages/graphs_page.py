import streamlit as st
import pandas as pd
import altair as alt
from kakeibo.db import get_monthly_summary


def _to_pandas(df):
    """Best-effort conversion to pandas.DataFrame (narwhals等に対応)."""
    if isinstance(df, pd.DataFrame):
        return df
    # narwhals: prefer to_native() if available, else to_pandas()
    to_native = getattr(df, "to_native", None)
    if callable(to_native):
        try:
            native = to_native()
            if isinstance(native, pd.DataFrame):
                return native
        except Exception:
            pass
    to_pandas = getattr(df, "to_pandas", None)
    if callable(to_pandas):
        try:
            native = to_pandas()
            if isinstance(native, pd.DataFrame):
                return native
        except Exception:
            pass
    # Fallback: try DataFrame constructor
    try:
        return pd.DataFrame(df)
    except Exception:
        return df


def render():
    st.title("収支推移グラフ")
    # Avoid Altair transforming DataFrames in ways that trigger narwhals warnings
    try:
        alt.data_transformers.disable_max_rows()
    except Exception:
        pass
    monthly_data = _to_pandas(get_monthly_summary())

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
    filtered_data = _to_pandas(monthly_data[mask])

    # Altair で直接描画（narwhals 警告回避のため pandas を直接渡す）
    base = (
        _to_pandas(filtered_data).reset_index()
        .rename(columns={filtered_data.index.name or "index": "month"})
        .assign(month=lambda d: pd.to_datetime(d["month"]))
    )

    st.subheader('月次収支（2023年10月以降）')
    long_df = base.melt(
        id_vars="month", value_vars=["収入", "支出"], var_name="type", value_name="total"
    )
    # Pass list-of-dicts to Altair to avoid any dataframe wrapping by Streamlit
    data1 = long_df.to_dict(orient="records")
    chart1 = (
        alt.Chart(alt.Data(values=data1))
        .mark_line(point=True)
        .encode(
            x=alt.X("month:T", title="月"),
            y=alt.Y("total:Q", title="金額"),
            color=alt.Color("type:N", title="種別"),
            tooltip=["month:T", "type:N", "total:Q"],
        )
    )
    st.altair_chart(chart1, use_container_width=True)

    st.subheader('累計資産推移（2023年10月以降）')
    data2 = base[["month", "累計資産"]].to_dict(orient="records")
    chart2 = (
        alt.Chart(alt.Data(values=data2))
        .mark_line(point=True)
        .encode(
            x=alt.X("month:T", title="月"),
            y=alt.Y("累計資産:Q", title="累計資産"),
            tooltip=["month:T", "累計資産:Q"],
        )
    )
    st.altair_chart(chart2, use_container_width=True)

    st.write("### 月次データ")
    st.dataframe(_to_pandas(filtered_data).style.format('{:,.0f}'))
