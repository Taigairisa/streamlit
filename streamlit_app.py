import streamlit as st
from google.oauth2 import service_account
import pandas as pd
import altair as alt
import gspread
import datetime
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
            question_category = question
            sheet.update_cell(targetRow + 1, num+1, question_category)
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
    convert_column_to_integer(df,"予算")

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
        val = date.isoformat()
        questions = [val, category, description, money]
        submitted = st.form_submit_button("送信")
    return questions, submitted

def makeTravelForm():
    with st.form("my_form", clear_on_submit=True):
        date = st.date_input(question_categories[0])
        category = st.text_input(label=question_categories[1])
        description = st.text_input(label=question_categories[2])
        money = st.text_input(question_categories[3])
        val = date.isoformat()
        questions = [val, category, description, money]
        submitted = st.form_submit_button("送信")
    return questions, submitted

def makeBudgetForm(categories):
    with st.form("my_form", clear_on_submit=True):
        date = st.date_input(question_categories[0])
        month = st.selectbox(label=question_categories[1],options=list(range(1, 13)))
        category = st.selectbox(label=question_categories[2], options=categories)
        money = st.text_input(question_categories[3])
        val = date.isoformat()
        questions = [val, month, category, money]
        submitted = st.form_submit_button("送信")
    return questions, submitted

def getThisMonthSummary(category):
    df = get_dataFrame(sh,category)
    today = datetime.date.today()
    this_month = today.strftime('%Y-%m')
    filtered_df = df[df['月'] == this_month]
    category_summary = filtered_df.groupby('カテゴリ')[category].sum().reset_index()
    return category_summary

def sideThisMonthRatio():
    today = datetime.date.today()
    df_used = getThisMonthSummary("支出").set_index("カテゴリ")
    df_budget = getThisMonthSummary("予算").set_index("カテゴリ")
    mixed_df = pd.concat([df_used,df_budget], axis=1).fillna(0)
    categories = ["食費/消耗品", "耐久消耗品","二人で遊ぶお金", "大河お小遣い", "幸華お小遣い"]
    mixed_df['割合'] = (mixed_df['支出'] / mixed_df['予算'])
    mixed_df = mixed_df.reindex(categories)
    st.sidebar.markdown(f" **【{today.month}月分】** {today.month}月{today.day}日時点の使用状況：")
    for index, row in mixed_df.iterrows():
        st.sidebar.progress(row['割合'], text=f"{index}：{int(row['支出'])}円 / {int(row['予算'])}円")

# スプレッドシートからデータ取得
SHEET_KEY = st.secrets.SP_SHEET_KEY.key # スプレッドシートのキー
scopes = [ 'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
credentials = service_account.Credentials.from_service_account_info( st.secrets["gcp_service_account"], scopes=scopes)
gc = gspread.authorize(credentials)
sh = gc.open_by_key(SHEET_KEY)

st.session_state["df_expenses"] = get_dataFrame(sh, "支出")
st.session_state["df_income"] = get_dataFrame(sh, "収入")
st.session_state["df_subscription"] = get_dataFrame(sh, "定期契約")
st.session_state["df_special"] = get_dataFrame(sh, "特別支出")
st.session_state["df_travel"] = get_dataFrame(sh, "旅行")

view_category = st.sidebar.selectbox(label="ページ変更", options=["入力フォーム","データ一覧","データ削除"])
st.sidebar.markdown("---")
sideThisMonthRatio()

import gspread_dataframe
if view_category == "入力フォーム":

    st.title("家計簿入力")
    input_category = st.selectbox(label="入力フォーム変更", options=["支出","収入","定期契約","特別支出","旅行","予算","残高"])
    if input_category == "支出":
        question_categories = ["日付", "カテゴリ", "詳細", "支出"]
        categories = ["食費/消耗品", "耐久消耗品","二人で遊ぶお金", "大河お小遣い", "幸華お小遣い"]
        questions, submitted = makeForm(categories)
        SP_SHEET = '支出'
    elif input_category == "収入":
        question_categories = ["日付", "カテゴリ", "詳細", "収入"]
        categories = ["大河給与", "幸華給与","大河投資","幸華投資", "贈与"]
        questions, submitted = makeForm(categories)
        SP_SHEET = '収入'
    elif input_category == "定期契約":
        question_categories = ["日付", "カテゴリ", "詳細", "支出"]
        categories = ["家賃", "電気代","ガス代","通信代", "サブスク","積み立て投資","その他"]
        questions, submitted = makeForm(categories)
        SP_SHEET = '定期契約'
    elif input_category == "特別支出":
        question_categories = ["日付", "カテゴリ", "詳細", "支出"]
        categories = ["病院", "イベント", "贈与", "その他"]
        questions, submitted = makeForm(categories)
        SP_SHEET = '特別支出'
    elif input_category == "旅行":
        question_categories = ["日付", "場所", "詳細", "支出"]
        questions, submitted = makeTravelForm()
        SP_SHEET = '旅行'
    elif input_category == "残高":
        question_categories = ["日付", "口座", "詳細","残高"]
        categories = ["三井住友", "京都信用金庫", "楽天銀行", "楽天証券", "JAバンク", "ゆうちょ", "松井バンク", "松井証券"]
        questions, submitted = makeForm(categories)
        SP_SHEET= '残高'
    else:
        question_categories = ["日付", "月", "カテゴリ", "予算"]
        categories = ["食費/消耗品", "耐久消耗品","二人で遊ぶお金", "大河お小遣い", "幸華お小遣い"]
        questions, submitted = makeBudgetForm(categories)
        SP_SHEET = '予算'

    worksheet = sh.worksheet(SP_SHEET)
    # 空の時にカラム名を埋め合わせる
    question_list = [[value] for value in question_categories]
    if is_worksheet_empty(worksheet):
        copyDataToBudgetSheet(question_list, worksheet)

    if submitted:
        with st.spinner("データ更新中..."):
            time.sleep(1.5)

        copyDataToBudgetSheet(questions, worksheet, True)
        result = pd.DataFrame([[category, answer] for category, answer in zip(question_categories, questions)]).set_index(0).T
        result.index = ["送信したデータ"]
        st.write(result)

elif view_category == "データ一覧":
    
    st.title("データ一覧")
    shown_data = st.selectbox(label="見たいデータを選択してください", options=["全データ", "資産推移", "カテゴリー別支出","収入推移", "定期契約推移", "特別支出推移", "旅行別"])
    if "全データ" in shown_data:
        input_category = st.select_slider(label="データを選択する",options=["支出","収入","定期契約","特別支出","旅行"])
        st.dataframe(get_dataFrame(sh, input_category))

    elif "資産推移" in shown_data:
        df_expenses = pd.concat([st.session_state["df_expenses"],st.session_state["df_special"],st.session_state["df_travel"],st.session_state["df_subscription"]])
        df_income = st.session_state["df_income"]
        df_transition = pd.concat([df_expenses, df_income]).fillna(0)
        df_transition['収支'] = df_transition["収入"]-df_transition["支出"]
        pivot_df = df_transition.pivot_table(index='月', values='収支', aggfunc='sum', fill_value=0).reset_index()
        
        df_balance = get_dataFrame(sh, "残高")
        today = datetime.date.today()
        this_month = today.strftime('%Y-%m')
        df_balance_today = df_balance[df_balance["月"]==this_month]
        balance_value_today = df_balance_today["残高"].astype(int).sum()

        pivot_df['収支'] = pivot_df["収支"] + balance_value_today
        st.line_chart(pivot_df.set_index('月'))

    elif "カテゴリー別支出" in shown_data:
        # 支出テーブルのみから集めたdf
        df = st.session_state["df_expenses"]
        selected_month = st.slider("月を選択してください", df['月'].unique())
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

    elif "収入推移" in shown_data:
        df = st.session_state["df_income"]
        pivot_df = df.pivot_table(index='月', columns='カテゴリ', values='収入', aggfunc='sum', fill_value=0).reset_index()
        monthly_total = pivot_df.groupby('月').sum()
        monthly_total['合計'] = monthly_total.sum(axis=1)

        st.line_chart(monthly_total['合計'])

    elif "定期契約推移" in shown_data:
        df = st.session_state["df_subscription"]
        selected_category = st.selectbox("カテゴリを選択してください",df['カテゴリ'].unique())
        category_total = df[df['カテゴリ'] == selected_category]
        pivot_df = category_total.pivot_table(index='月', columns='カテゴリ', values='支出', aggfunc='sum', fill_value=0).reset_index()
        monthly_total = pivot_df.groupby('月').sum()
        monthly_total['合計'] = monthly_total.sum(axis=1)

        st.line_chart(monthly_total['合計'])

    elif "特別支出推移" in shown_data:
        df = st.session_state["df_special"]
        selected_category = st.selectbox("カテゴリを選択してください",df['カテゴリ'].unique())
        category_total = df[df['カテゴリ'] == selected_category]
        pivot_df = category_total.pivot_table(index='月', columns='カテゴリ', values='支出', aggfunc='sum', fill_value=0).reset_index()
        monthly_total = pivot_df.groupby('月').sum()
        monthly_total['合計'] = monthly_total.sum(axis=1)

        st.line_chart(monthly_total['合計'])
    elif "旅行別" in shown_data:
        df = st.session_state["df_travel"]
        category_summary = df.groupby('場所')['支出'].sum().reset_index()
        bars = (
            alt.Chart(category_summary)
            .mark_bar()
            .encode(
                x="場所:N",
                y=alt.Y("支出:Q"),
                color="場所:N",
            )
        )
        st.altair_chart(bars, use_container_width=True)
        st.dataframe(category_summary)

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

