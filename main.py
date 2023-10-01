import streamlit as st
import numpy as np
import pandas as pd
import time

import gspread
import pandas as pd
from google.oauth2 import service_account
from PIL import Image
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import altair as alt

def count_rows(sheet):
    values = sheet.get_all_values()
    return len(values)

def count_columns(sheet):
    values = sheet.get_all_values()
    if not values:
        return 0  # シートにデータがない場合、0を返す

    # 各行の列数を調べて最大の列数を取得
    max_column_count = max(len(row) for row in values)
    return max_column_count

def copyDataToBudgetSheet(questions, sheet, lastRow = False):
    if lastRow:
        targetRow = count_rows(sheet)  # 家計簿シートに追加する行
        for num, question in enumerate(questions):
            question_category, answer = question[0], question[1]
            sheet.update_cell(targetRow + 1, num+1, answer)
    else:
        targetRow = 0
        for num, question in enumerate(questions):
            question_category = question[0]
            sheet.update_cell(targetRow + 1, num+1, question_category)
    # フォームからのデータをリストとして受け取る

question_categories = ["日付", "カテゴリ", "詳細", "収入", "支出"]

# スプレッドシートの認証
scopes = [ 'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'
]
credentials = service_account.Credentials.from_service_account_info( st.secrets["gcp_service_account"], scopes=scopes
)
gc = gspread.authorize(credentials)
# スプレッドシートからデータ取得
SHEET_KEY = st.secrets.SP_SHEET_KEY.key # スプレッドシートのキー
sh = gc.open_by_key(SHEET_KEY)
SP_SHEET = 'シート1' # シート名「シート1」を指定 # シート名「シート1」を指定
worksheet = sh.worksheet(SP_SHEET)

question_list = [[value] for value in question_categories]
copyDataToBudgetSheet(question_list, worksheet)

st.sidebar.write("""
    ## データを見る
""")
st.sidebar.slider("ウィジェット",1,50,20)
row_data_button = st.sidebar.checkbox("生データを見る")
monthly_transition_button = st.sidebar.checkbox("資産推移を見る")
monthly_category_button = st.sidebar.checkbox("月ごとの収支を見る")

categories = ["給与", "二人で遊ぶお金", "食費/消耗品", "耐久消耗品", "お小遣い", "楽天証券前月比", "その他"]

with st.form("my_form", clear_on_submit=True):
    date = st.date_input(question_categories[0])
    category = st.selectbox(label=question_categories[1], options=categories)
    description = st.text_area(question_categories[2])
    income = st.text_input(question_categories[3])
    expense = st.text_input(question_categories[4])
    submitted = st.form_submit_button("送信")

if submitted:
    with st.spinner("データ更新中..."):
        time.sleep(1)
    val = date.isoformat()
    questions = [val, category, description, income, expense]
    result = [[category, answer] for category, answer in zip(question_categories, questions)]
    copyDataToBudgetSheet(result, worksheet, True)

def get_dataFrame(sheet_key, sheet):
    sh = gc.open_by_key(sheet_key)
    
    worksheet = sh.worksheet(sheet)
    data = worksheet.get_all_values() # シート内の全データを取得
    df = pd.DataFrame(data[1:], columns=data[0]) # 取得したデータをデータフレームに変換 
    df["収入"] = df["収入"].replace('', '0').astype(int)
    df["支出"] =df["支出"].replace('', '0').astype(int)

    # 日付列を日付型に変換
    df['日付'] = pd.to_datetime(df['日付'], format='ISO8601')

    df['月'] = df['日付'].dt.strftime('%Y-%m')
    df['収支'] = df['収入'] - df['支出']

    return df

if row_data_button:
    st.dataframe(get_dataFrame(SHEET_KEY, SP_SHEET))

if monthly_transition_button:
    df = get_dataFrame(SHEET_KEY, SP_SHEET)
    pivot_df = df.pivot_table(index='月', columns='カテゴリ', values='収支', aggfunc='sum', fill_value=0).reset_index()
    #cat_monthly_summary = df.groupby(['月', 'カテゴリ'])['支出'].sum().reset_index()

    # 月別合計収支を作りたい
    monthly_total = pivot_df.groupby('月').sum()

    # 合計列を追加
    monthly_total['合計'] = monthly_total.sum(axis=1)

    st.line_chart(monthly_total['合計'])

if monthly_category_button:
    df = get_dataFrame(SHEET_KEY, SP_SHEET)
    # 月の選択用Expander
    selected_month = st.selectbox("月を選択してください", df['月'].unique())

    # 選択された月のデータをフィルタリング
    filtered_df = df[df['月'] == selected_month]

    # グラフのプロット
    st.subheader(f"{selected_month}の各カテゴリーごとの収支")

    # グラフのプロット用のデータを準備
    category_summary = filtered_df.groupby('カテゴリ')['収支'].sum().reset_index()
    # # 棒グラフのプロット
    bars = (
        alt.Chart(category_summary)
        .mark_bar()
        .encode(
            x="カテゴリ:N",
            y=alt.Y("収支:Q"),
            color="カテゴリ:N",
        )
    )

    st.altair_chart(bars, use_container_width=True)

    # chart =(
    #     alt.Chart(category_summary)
    #     .mark_line(opacity=0.8)
    #     .encode(
    #         x="カテゴリ:N",
    #         y=alt.Y("収支:Q", stack=None),
    #         color="カテゴリ:N"
    #     )
    # )
    # plt.figure(figsize=(10, 6))
    # sns.barplot(x='カテゴリ', y='収支', data=category_summary)
    # plt.xlabel('カテゴリ')
    # plt.ylabel('収支')
    # plt.xticks(rotation=45)
    # plt.title(f"{selected_month}の各カテゴリーごとの収支")
    # st.pyplot(plt)
    #melt
    #loc      



    



# st.write("プログレスバー")
# "start!!"
# latest_iteration = st.empty()
# bar = st.progress(0)
# for i in range(100):
#     latest_iteration.text(f"iteration{i+1}")
#     bar.progress(i+1)
#     time.sleep(0.1)
