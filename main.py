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

def column_exists(df, column_name):
    return column_name in df.columns

# カラムが存在する場合にそのカラムを整数型に変換する関数
def convert_column_to_integer(df, column_name):
    if column_exists(df, column_name):
        df[column_name] = df[column_name].replace('', '0').astype(int)

def get_dataFrame(sh, sheet): 
    worksheet = sh.worksheet(sheet)
    data = worksheet.get_all_values() # シート内の全データを取得
    df = pd.DataFrame(data[1:], columns=data[0]) # 取得したデータをデータフレームに変換 

    convert_column_to_integer(df,"収入")
    convert_column_to_integer(df,"支出")
    convert_column_to_integer(df,"収支")

    # 日付列を日付型に変換
    df['日付'] = pd.to_datetime(df['日付'], format='ISO8601')
    df['月'] = df['日付'].dt.strftime('%Y-%m')

    return df

def makeForm(categories):
    with st.form("my_form", clear_on_submit=True):
        date = st.date_input(question_categories[0])
        category = st.selectbox(label=question_categories[1], options=categories)
        description = st.text_input(label=question_categories[2])
        money = st.text_input(question_categories[3])
        submitted = st.form_submit_button("送信")
    return date, category, description, money, submitted

# スプレッドシートからデータ取得
SHEET_KEY = st.secrets.SP_SHEET_KEY.key # スプレッドシートのキー
scopes = [ 'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
credentials = service_account.Credentials.from_service_account_info( st.secrets["gcp_service_account"], scopes=scopes)
gc = gspread.authorize(credentials)
sh = gc.open_by_key(SHEET_KEY)

st.sidebar.write("""
    ## データを見る
""")
st.sidebar.slider("ウィジェット",1,50,20)
view_category = st.sidebar.selectbox(label="ページ変更", options=["入力フォーム","データ一覧","データ削除"])

import gspread_dataframe
if view_category == "入力フォーム":

    st.title("家計簿入力")
    input_category = st.selectbox(label="入力フォーム変更", options=["支出","収入","定期契約","特別支出"])
    if input_category == "支出":
        question_categories = ["日付", "カテゴリ", "詳細", "支出"]
        categories = ["二人で遊ぶお金", "食費/消耗品", "耐久消耗品", "大河お小遣い", "幸華お小遣い"]
        date, category, description, money, submitted = makeForm(categories)
        SP_SHEET = '支出'
    elif input_category == "収入":
        question_categories = ["日付", "カテゴリ", "詳細", "収入"]
        categories = ["大河給与", "幸華給与","大河投資","幸華投資", "贈与"]
        date, category, description, money, submitted = makeForm(categories)
        SP_SHEET = '収入'
    elif input_category == "定期契約":
        question_categories = ["日付", "カテゴリ", "詳細", "支出"]
        categories = ["家賃", "電気代","ガス代","通信代", "サブスク","その他"]
        date, category, description, money, submitted = makeForm(categories)
        SP_SHEET = '定期契約'
    else:
        question_categories = ["日付", "カテゴリ", "詳細", "支出"]
        categories = ["病院", "旅行", "イベント", "贈与", "その他"]
        date, category, description, money, submitted = makeForm(categories)
        SP_SHEET = '特別支出'

    worksheet = sh.worksheet(SP_SHEET)
    # 空の時にカラム名を埋め合わせる
    question_list = [[value] for value in question_categories]
    if is_worksheet_empty(worksheet):
        copyDataToBudgetSheet(question_list, worksheet)

    if submitted:
        with st.spinner("データ更新中..."):
            time.sleep(1)
        val = date.isoformat()
        questions = [val, category, description, money]
        result = [[category, answer] for category, answer in zip(question_categories, questions)]
        copyDataToBudgetSheet(result, worksheet, True)

elif view_category == "データ一覧":
    
    st.title("データ一覧")
    shown_data = st.multiselect("見たいデータを選択してください", ["全データ", "資産推移", "月ごとの支出", "電気代推移", "ガス代推移", "その他推移"], default = None)
    # row_data_button = st.checkbox("生データを見る")
    # monthly_transition_button = st.checkbox("資産推移を見る")
    # monthly_category_button = st.checkbox("月ごとの収支を見る")
    if "全データ" in shown_data:
        input_category = st.select_slider(label="データを選択する",options=["支出","収入","定期契約","特別支出"])
        st.dataframe(get_dataFrame(sh, input_category))

    # if monthly_transition_button:
    #     # 支出テーブルと収入テーブルのその月のものを全部足したdf
    #     df = 
    #     pivot_df = df.pivot_table(index='月', columns='カテゴリ', values='収支', aggfunc='sum', fill_value=0).reset_index()
    #     monthly_total = pivot_df.groupby('月').sum()
    #     monthly_total['合計'] = monthly_total.sum(axis=1)

    #     st.line_chart(monthly_total['合計'])

    if "月ごとの支出" in shown_data:
        # 支出テーブルのみから集めたdf
        df = get_dataFrame(sh, "支出")
        selected_month = st.selectbox("月を選択してください", df['月'].unique())
        filtered_df = df[df['月'] == selected_month]
        st.subheader(f"{selected_month}の各カテゴリーごとの支出")
        category_summary = filtered_df.groupby('カテゴリ')['支出'].sum().reset_index()
        bars = (
            alt.Chart(category_summary)
            .mark_bar()
            .encode(
                x="カテゴリ:N",
                y=alt.Y("支出:Q"),
                color="カテゴリ:N",
            )
        )

        st.altair_chart(bars, use_container_width=True)
        st.dataframe(filtered_df)

elif view_category == "データ削除":
    reload_button = st.button("更新")
    # ページをリロードするJavaScriptコードを実行
    if reload_button:
        st.write("<script>window.location.reload();</script>", unsafe_allow_html=True)
    
    input_category = st.select_slider(label="データを選択する",options=["支出","収入","定期契約","特別支出"])
    worksheet = sh.worksheet(input_category)
    df = get_dataFrame(sh, input_category)
    display = st.dataframe(df)
    with st.form("my_form", clear_on_submit=True):
        selected_row_indices = st.multiselect("削除したい行を選択", list(df[::-1].index)) 
        submitted = st.form_submit_button("データを削除")

    if submitted:
        st.write("消したデータ：")
        st.table(df.iloc[selected_row_indices])
        df = df.drop(selected_row_indices)  # 選択された行を削除
        worksheet.clear()
        gspread_dataframe.set_with_dataframe(worksheet,df)
        st.write("<script>window.location.reload();</script>", unsafe_allow_html=True)


# elif input_category == "収入":
#     with st.form("my_form", clear_on_submit=True):
#         date = st.date_input(question_categories[0])
#         category = st.selectbox(label=question_categories[1], options=categories)
#         if category != "選択してください":
#         if category == "給与":
#             description = st.selectbox(label="詳細 (選択)", options=["大河", "幸華"])
#             income = st.text_input(label=question_categories[3])
#             expense = 0
#         elif category == "その他":
#             description = st.selectbox(label="詳細 (選択)", options= ["病院", "旅行", "イベント", "贈与", "その他"])
#             income = 0
#             expense = st.text_input(question_categories[4])
#         elif category == "楽天証券前月比":
#             income = st.text_input(label=question_categories[3])
#             expense = 0
#     submitted = st.form_submit_button("送信")
    

# if submitted:
#     if category == "選択してください":
#         st.error("カテゴリーを選択してください")
#         st.stop()
#     with st.spinner("データ更新中..."):
#         time.sleep(1)
#     val = date.isoformat()
#     questions = [val, category, description, income, expense]
#     result = [[category, answer] for category, answer in zip(question_categories, questions)]
#     copyDataToBudgetSheet(result, worksheet, True)
#     df = get_dataFrame(SHEET_KEY, SP_SHEET)


######################################

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