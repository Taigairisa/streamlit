import streamlit as st
from google.oauth2 import service_account
import pandas as pd
import altair as alt
import gspread
import datetime
import time
import gspread_dataframe

def copyDataToBudgetSheet(questions, sheet, lastRow = False):
    if lastRow:
        sheet.append_row(questions)
    else:
        for num, question in enumerate(questions):
            sheet.update_cell(1, num + 1, question)

def is_worksheet_empty(worksheet):
    cell_list = worksheet.get_all_values()
    if not cell_list:
        return True
    return False

# カラムが存在する場合にそのカラムを整数型に変換する関数
def convert_column_to_integer(df, column_name):
    if column_name in df.columns:
        df[column_name] = df[column_name].replace('', '0').astype(int)

def makeForm(categories, question_categories):
    with st.form("my_form", clear_on_submit=True):
        date = st.date_input(question_categories[0])
        category = st.selectbox(label=question_categories[1], options=categories)
        description = st.text_input(label=question_categories[2])
        money = st.text_input(question_categories[3])
        questions = [date.isoformat(), category, description, (money)]
        submitted = st.form_submit_button("送信")
    return questions, submitted

def makeBudgetForm(categories, question_categories):
    with st.form("my_form", clear_on_submit=True):
        date = st.date_input(question_categories[0])
        month = st.selectbox(label=question_categories[1], options=list(range(1, 13)))
        category = st.selectbox(label=question_categories[2], options=categories)
        money = st.text_input(question_categories[3])
        questions = [date.isoformat(), month, category, (money)]
        submitted = st.form_submit_button("送信")
    return questions, submitted

def makeTravelForm(question_categories):
    with st.form("my_form", clear_on_submit=True):
        date = st.date_input(question_categories[0])
        category = st.text_input(label=question_categories[1])
        description = st.text_input(label=question_categories[2])
        money = st.text_input(question_categories[3])
        questions = [date.isoformat(), category, description, (money)]
        submitted = st.form_submit_button("送信")
    return questions, submitted

def get_question_categories(input_category):
    if input_category == "支出":
        question_categories = ["日付", "カテゴリ", "詳細", "支出"]
        categories = ["食費/消耗品", "耐久消耗品","二人で遊ぶお金", "大河お小遣い", "幸華お小遣い"]
    elif input_category == "収入":
        question_categories = ["日付", "カテゴリ", "詳細", "収入"]
        categories = ["大河給与", "幸華給与","大河投資","幸華投資", "贈与"]
    elif input_category == "定期契約":
        question_categories = ["日付", "カテゴリ", "詳細", "支出"]
        categories = ["家賃", "電気代","ガス代","通信代", "サブスク","積み立て投資","その他"]
    elif input_category == "特別支出":
        question_categories = ["日付", "カテゴリ", "詳細", "支出"]
        categories = ["病院", "イベント", "贈与", "その他"]
    elif input_category == "旅行":
        question_categories = ["日付", "場所", "詳細", "支出"]
        categories = []
    elif input_category == "残高":
        question_categories = ["日付", "口座", "詳細","残高"]
        categories = ["三井住友", "京都信用金庫", "楽天銀行", "楽天証券", "JAバンク", "ゆうちょ", "松井バンク", "松井証券"]
    elif input_category == "予算":
        question_categories = ["日付", "月", "カテゴリ", "予算"]
        categories = ["食費/消耗品", "耐久消耗品","二人で遊ぶお金", "大河お小遣い", "幸華お小遣い"]
    return question_categories, categories

def getThisMonthSummary(category, date):
    df = get_dataframe_from_sheet(sh,category)
    this_month = date.strftime('%Y/%m')
    filtered_df = df[df['月'] == this_month]
    category_summary = filtered_df.groupby('カテゴリ')[category].sum().reset_index().set_index("カテゴリ")
    return category_summary

def sideThisMonthRatio():
    today = datetime.date.today()
    categories = ["食費/消耗品", "耐久消耗品","二人で遊ぶお金", "大河お小遣い", "幸華お小遣い"]
    
    df_used = getThisMonthSummary("支出", today)
    df_budget = getThisMonthSummary("予算", today)

    mixed_df = pd.concat([df_used,df_budget], axis=1).fillna(0)
    mixed_df['割合'] = mixed_df['支出'] / mixed_df['予算']
    return today, mixed_df.reindex(categories)

@st.cache_resource(ttl = 600, show_spinner=False)
def get_worksheet_from_gspread_client():
    credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT, scopes=SPREADSHEET_SCOPES)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    return sh

@st.cache_data(ttl = 120, show_spinner=False)
def get_dataframe_from_sheet(_sh, sheet_name):
    worksheet = _sh.worksheet(sheet_name)
    # worksheet = get_worksheet(_gc, sheet_name)
    data = worksheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
    convert_column_to_integer(df,"収入")
    convert_column_to_integer(df,"支出")
    convert_column_to_integer(df,"収支")
    convert_column_to_integer(df,"予算")

    # 日付列を日付型に変換
    df['日付'] = pd.to_datetime(df['日付'], format='ISO8601')
    df['月'] = df['日付'].dt.strftime('%Y/%m')
    return df

def cache_clear():
    st.cache_data.clear()

def reflect_all_data(sh):
    st.session_state["df_expenses"] = get_dataframe_from_sheet(sh, "支出")
    st.session_state["df_income"] = get_dataframe_from_sheet(sh, "収入")
    st.session_state["df_subscription"] = get_dataframe_from_sheet(sh, "定期契約")
    st.session_state["df_special"] = get_dataframe_from_sheet(sh, "特別支出")
    st.session_state["df_travel"] = get_dataframe_from_sheet(sh, "旅行")

def side_bar():
    with st.sidebar:
        view_category = st.selectbox(label="ページ変更", options=["入力フォーム","データ一覧","データ削除"])
        st.markdown("---")
        today, mixed_df = sideThisMonthRatio()
        st.markdown(f" **【{today.month}月分】** {today.month}月{today.day}日時点の使用状況：")
        for index, row in mixed_df.iterrows():
            if row['割合'] >= 1:
                st.write('限度額を超えています!')
                st.progress(100, text=f"{index}：{int(row['支出'])}円 / {int(row['予算'])}円")
            else:
                st.progress(row['割合'], text=f"{index}：{int(row['支出'])}円 / {int(row['予算'])}円")

    return view_category

def get_pivot_df(df):
        pivot_df = pd.DataFrame()
        if '支出' in df.columns:
            pivot_df = df.pivot_table(index='月', columns='カテゴリ', values='支出', aggfunc='sum', fill_value=0)
        elif '収入' in df.columns:
            pivot_df = df.pivot_table(index='月', columns='カテゴリ', values='収入', aggfunc='sum', fill_value=0)
        monthly_total = pivot_df.groupby('月').sum()
        monthly_total['合計'] = monthly_total.sum(axis=1)
        return pd.concat([pivot_df, monthly_total['合計']], axis=1)

# グローバル変数の設定
SHEET_KEY = st.secrets.SP_SHEET_KEY.key
SPREADSHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT = st.secrets["gcp_service_account"]

st.set_page_config(page_title="家計簿アプリ", initial_sidebar_state="expanded")

sh = get_worksheet_from_gspread_client()
reflect_all_data(sh)
view_category = side_bar()

if view_category == "入力フォーム":

    st.title("家計簿入力")
    
    input_category = st.selectbox(label="入力フォーム変更", options=["支出","収入","定期契約","特別支出","旅行","予算","残高"])
    question_categories, categories = get_question_categories(input_category)

    if input_category in ["支出", "収入", "定期契約", "特別支出", "残高"]:
        questions, submitted = makeForm(categories, question_categories)
        SP_SHEET = input_category
    elif input_category == "旅行":
        questions, submitted = makeTravelForm(question_categories)
        SP_SHEET = input_category
    elif input_category == "予算":
        questions, submitted = makeBudgetForm(categories, question_categories)
        SP_SHEET = input_category

    worksheet = sh.worksheet(SP_SHEET)

    # 空の時にカラム名を埋め合わせる
    if is_worksheet_empty(worksheet):
        copyDataToBudgetSheet(question_categories, worksheet)

    if submitted:
        copyDataToBudgetSheet(questions, worksheet, True)
        st.session_state.result = pd.DataFrame([[category, answer] for category, answer in zip(question_categories, questions)]).set_index(0).T
        st.session_state.result.index = ["送信したデータ"]
        st.write(st.session_state.result)
        time.sleep(1.5)
        cache_clear()
        st.rerun()
        # st.write("<script>window.location.reload();</script>", unsafe_allow_html=True)

elif view_category == "データ一覧":
    
    st.title("データ一覧")
    shown_data = st.selectbox(label="見たいデータを選択してください", options=["全データ", "資産推移", "カテゴリー別支出","収入推移", "定期契約推移", "特別支出推移", "旅行別"])
    if "全データ" in shown_data:
        options=["支出","収入","定期契約","特別支出","旅行","予算","残高"]
        input_categories = st.tabs(options)
        for n, input_category in enumerate(input_categories):
            input_category.dataframe(get_dataframe_from_sheet(sh, options[n]).drop(columns=['月']))

    elif "資産推移" in shown_data:
        df_expenses = pd.concat([st.session_state["df_expenses"],st.session_state["df_special"],st.session_state["df_travel"],st.session_state["df_subscription"]])
        df_income = st.session_state["df_income"]
        df_transition = pd.concat([df_expenses, df_income]).fillna(0)
        df_transition['収支'] = df_transition["収入"]-df_transition["支出"]
        pivot_df = df_transition.pivot_table(index='月', values='収支', aggfunc='sum', fill_value=0).reset_index()
        
        df_balance = get_dataframe_from_sheet(sh, "残高")
        today = datetime.date.today()
        this_month = today.strftime('%Y/%m')
        df_balance_today = df_balance[df_balance["月"]==this_month]
        balance_value_today = df_balance_today["残高"].astype(int).sum()

        pivot_df['収支'] = pivot_df["収支"] + balance_value_today
        st.line_chart(pivot_df.set_index('月'))

    elif "カテゴリー別支出" in shown_data:
        # 支出テーブルのみから集めたdf
        df = st.session_state["df_expenses"]
        pivot_df = get_pivot_df(df)
        selected_category = st.multiselect('グラフに表示する国を選択', list(pivot_df.columns), default = "合計")
        selected_df = pivot_df[selected_category] 
        st.dataframe(selected_df.T)
        st.line_chart(selected_df)

        if st.checkbox("月別に表示する"):
            selected_month = st.select_slider("月を選択してください", list(sorted(df['月'].unique())) )
            filtered_df = df[df['月'] == selected_month]
            # st.dataframe(filtered_df)
            st.subheader(f"{selected_month}の各カテゴリーごとの支出")
            category_summary = filtered_df.groupby('カテゴリ')['支出'].sum().reset_index()
            st.dataframe(category_summary)
            bars = (
                alt.Chart(category_summary)
                .mark_bar()
                .encode(x="カテゴリ:N",y=alt.Y("支出:Q"),color="カテゴリ:N",)
            )

            st.altair_chart(bars, use_container_width=True)
            st.dataframe(filtered_df)

    elif "収入推移" in shown_data:
        df = st.session_state["df_income"]
        pivot_df = get_pivot_df(df)
        selected_category = st.multiselect('グラフに表示する国を選択', list(pivot_df.columns), default = "合計")
        selected_df = pivot_df[selected_category] 
        st.dataframe(selected_df.T)
        st.line_chart(selected_df)
        
        if st.checkbox("月別に表示する"):
            selected_month = st.select_slider("月を選択してください", list(sorted(df['月'].unique())) )
            filtered_df = df[df['月'] == selected_month]
            st.subheader(f"{selected_month}の各カテゴリーごとの収入")
            category_summary = filtered_df.groupby('カテゴリ')['収入'].sum().reset_index()
            bars = (
                alt.Chart(category_summary)
                .mark_bar()
                .encode(x="カテゴリ:N",y=alt.Y("収入:Q"),color="カテゴリ:N",)
            )

            st.altair_chart(bars, use_container_width=True)
            st.dataframe(filtered_df)

    elif "定期契約推移" in shown_data:
        df = st.session_state["df_subscription"]
        pivot_df = get_pivot_df(df)
        selected_category = st.multiselect('グラフに表示する国を選択', list(pivot_df.columns), default = "合計")
        selected_df = pivot_df[selected_category] 
        st.dataframe(selected_df.T)
        st.line_chart(selected_df)

        if st.checkbox("月別に表示する"):
            selected_month = st.select_slider("月を選択してください", list(sorted(df['月'].unique())) )
            filtered_df = df[df['月'] == selected_month]
            st.subheader(f"{selected_month}の各カテゴリーごとの収入")
            category_summary = filtered_df.groupby('カテゴリ')['支出'].sum().reset_index()
            bars = (
                alt.Chart(category_summary)
                .mark_bar()
                .encode(x="カテゴリ:N",y=alt.Y("支出:Q"),color="カテゴリ:N",)
            )

            st.altair_chart(bars, use_container_width=True)
            st.dataframe(filtered_df)

    elif "特別支出推移" in shown_data:
        df = st.session_state["df_special"]
        st.dataframe(df)
        pivot_df = get_pivot_df(df)
        selected_category = st.multiselect('グラフに表示する国を選択', list(pivot_df.columns), default = "合計")
        selected_df = pivot_df[selected_category] 
        st.dataframe(selected_df.T)
        st.line_chart(selected_df)

        if st.checkbox("月別に表示する"):
            selected_month = st.select_slider("月を選択してください", list(sorted(df['月'].unique())) )
            filtered_df = df[df['月'] == selected_month]
            st.subheader(f"{selected_month}の各カテゴリーごとの収入")
            category_summary = filtered_df.groupby('カテゴリ')['支出'].sum().reset_index()
            bars = (
                alt.Chart(category_summary)
                .mark_bar()
                .encode(x="カテゴリ:N",y=alt.Y("支出:Q"),color="カテゴリ:N",)
            )

            st.altair_chart(bars, use_container_width=True)
            st.dataframe(filtered_df)

    elif "旅行別" in shown_data:
        df = st.session_state["df_travel"]
        category_summary = df.groupby('場所')['支出'].sum().reset_index()
        bars = (
            alt.Chart(category_summary)
            .mark_bar()
            .encode(x="場所:N",y=alt.Y("支出:Q"),color="場所:N",)
        )
        st.altair_chart(bars, use_container_width=True)
        st.dataframe(category_summary)

elif view_category == "データ削除":

    input_category = st.selectbox(label="データを選択する",options=["支出","収入","定期契約","特別支出","旅行","予算","残高"])
    worksheet = sh.worksheet(input_category) 
    df = get_dataframe_from_sheet(sh, input_category).drop(columns=['月'])
    df = st.data_editor(df, num_rows="dynamic")
    with st.form("my_form", clear_on_submit=True):
        submitted = st.form_submit_button("データを編集")
    if submitted:
        worksheet.clear()
        gspread_dataframe.set_with_dataframe(worksheet,df)
        cache_clear()
        st.rerun()

