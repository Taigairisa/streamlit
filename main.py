import streamlit as st
from google.oauth2 import service_account
import pandas as pd
import altair as alt
import gspread
import time

def count_rows(sheet):
    values = sheet.get_all_values()
    return len(values)

def count_columns(sheet):
    values = sheet.get_all_values()
    if not values:
        return 0  
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

def is_worksheet_empty(worksheet):
    cell_list = worksheet.get_all_values()
    if not cell_list:
        return True
    return False

def getWorkSheet(sheet_key, sheet): # スプレッドシートの認証
    scopes = [ 'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'
    ]
    credentials = service_account.Credentials.from_service_account_info( st.secrets["gcp_service_account"], scopes=scopes
    )
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(sheet_key)
    worksheet = sh.worksheet(sheet)
    return worksheet

def get_dataFrame(sheet_key, sheet): 
    worksheet = gc.open_by_key(sheet_key).worksheet(sheet)
    data = worksheet.get_all_values() # シート内の全データを取得
    df = pd.DataFrame(data[1:], columns=data[0]) # 取得したデータをデータフレームに変換 
    df["収入"] = df["収入"].replace('', '0').astype(int)
    df["支出"] =df["支出"].replace('', '0').astype(int)

    # 日付列を日付型に変換
    df['日付'] = pd.to_datetime(df['日付'], format='ISO8601')
    df['月'] = df['日付'].dt.strftime('%Y-%m')
    df['収支'] = df['収入'] - df['支出']

    return df

# スプレッドシートからデータ取得
SHEET_KEY = st.secrets.SP_SHEET_KEY.key # スプレッドシートのキー
SP_SHEET = 'シート1' # シート名「シート1」を指定 # シート名「シート1」を指定

scopes = [ 'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'
]
credentials = service_account.Credentials.from_service_account_info( st.secrets["gcp_service_account"], scopes=scopes
)
gc = gspread.authorize(credentials)
sh = gc.open_by_key(SHEET_KEY)
worksheet = sh.worksheet(SP_SHEET)

worksheet = getWorkSheet(SHEET_KEY, SP_SHEET)
question_categories = ["日付", "カテゴリ", "詳細", "収入", "支出"]
question_list = [[value] for value in question_categories]
if is_worksheet_empty(worksheet):
    copyDataToBudgetSheet(question_list, worksheet)
df = get_dataFrame(SHEET_KEY, SP_SHEET)

st.sidebar.write("""
    ## データを見る
""")
st.sidebar.slider("ウィジェット",1,50,20)
row_data_button = st.sidebar.checkbox("生データを見る")
monthly_transition_button = st.sidebar.checkbox("資産推移を見る")
monthly_category_button = st.sidebar.checkbox("月ごとの収支を見る")

categories = ["選択してください","二人で遊ぶお金", "食費/消耗品", "耐久消耗品", "お小遣い","その他", "給与", "楽天証券前月比"]

st.title("家計簿入力")

css = """
    <style>
        .custom-container {
            padding: 10px;
            border: 2px solid gray;
            border-radius: 5px;
        }
    </style>
"""

# StreamlitでCSSを表示
st.markdown(css, unsafe_allow_html=True)

with st.container() as container:
     date = st.date_input(question_categories[0])
     category = st.selectbox(label=question_categories[1], options=categories)
     if category != "選択してください":
        # カテゴリーに応じて説明、収入、支出の入力フィールドを動的に変更
        if category == "給与":
            description = st.selectbox(label="詳細 (選択)", options=["大河", "幸華"])
            income = st.text_input(label=question_categories[3])
        elif category == "その他":
            description = st.selectbox(label="詳細 (選択)", options= ["病院", "旅行", "イベント", "贈与", "その他"])
            expense = st.text_input(question_categories[4])
        elif category == "楽天証券前月比":
            income = st.text_input(label=question_categories[3])
        elif category == "お小遣い":
            description_label = "詳細 (選択)"
            description = st.selectbox(label="詳細 (選択)", options= ["大河", "幸華"])
            expense = st.text_input(question_categories[4])
        else:
            description = st.text_input(label="詳細 (テキスト)")
            expense = st.text_input(question_categories[4])
     submitted = st.button("送信")
    
# with st.form("my_form", clear_on_submit=True):
#     date = st.date_input(question_categories[0])
#     category = st.selectbox(label=question_categories[1], options=categories)
#     if category != "選択してください":
#         # カテゴリーに応じて説明、収入、支出の入力フィールドを動的に変更
#         if category == "給与" or category == "お小遣い":
#             description_label = "詳細 (選択)"
#             description_options = ["大河", "幸華"]
#             income_label = "収入"
#             expense_label = "支出"
#         elif category == "その他":
#             description_label = "詳細 (選択)"
#             description_options = ["病院", "旅行", "イベント", "贈与", "その他"]
#             income_label = "収入"
#             expense_label = "支出"
#         else:
#             description_label = "詳細"
#             description_options = st.text_input(label="詳細 (テキスト)")
#             income_label = "収入"
#             expense_label = "支出"

#         description = st.selectbox(label=description_label, options=description_options)
#         income = st.text_input(label=income_label)
#         expense = st.text_input(label=expense_label)
#     # income = st.text_input(question_categories[3])
#     # expense = st.text_input(question_categories[4])
#     submitted = st.form_submit_button("送信")

if submitted:
    if category == "選択してください":
        st.error("カテゴリーを選択してください")
        st.stop()
    with st.spinner("データ更新中..."):
        time.sleep(1)
    val = date.isoformat()
    questions = [val, category, description, income, expense]
    result = [[category, answer] for category, answer in zip(question_categories, questions)]
    copyDataToBudgetSheet(result, worksheet, True)
    df = get_dataFrame(SHEET_KEY, SP_SHEET)

if row_data_button:
    st.dataframe(get_dataFrame(SHEET_KEY, SP_SHEET))

if monthly_transition_button:
    pivot_df = df.pivot_table(index='月', columns='カテゴリ', values='収支', aggfunc='sum', fill_value=0).reset_index()
    monthly_total = pivot_df.groupby('月').sum()
    monthly_total['合計'] = monthly_total.sum(axis=1)

    st.line_chart(monthly_total['合計'])

if monthly_category_button:
    selected_month = st.selectbox("月を選択してください", df['月'].unique())
    filtered_df = df[df['月'] == selected_month]
    st.subheader(f"{selected_month}の各カテゴリーごとの収支")
    category_summary = filtered_df.groupby('カテゴリ')['収支'].sum().reset_index()
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
