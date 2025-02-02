from pathlib import Path
import sqlite3
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import streamlit as st
import pandas as pd
from collections import defaultdict
from google.oauth2 import service_account
import gspread
import pygwalker as pyg
import streamlit.components.v1 as components
# import streamlit_authenticator as stauth

SHEET_KEY = st.secrets.SP_SHEET_KEY.key
SPREADSHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT = st.secrets["gcp_service_account"]
DB_FILENAME = Path(__file__).parent / "kakeibo.db"



def get_worksheet_from_gspread_client():
    credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT, scopes=SPREADSHEET_SCOPES)
    gc = gspread.authorize(credentials)
    return gc.open_by_key(SHEET_KEY)

def exists_db_file():
    return DB_FILENAME.exists()

def connect_db():
    return sqlite3.connect(DB_FILENAME)

def initialize_data(conn, sh):
    cursor = conn.cursor()
    create_tables(cursor)
    insert_initial_categories(cursor)
    insert_initial_sub_categories(cursor)
    insert_transactions_from_sheets(cursor, sh)
    conn.commit()
    conn.close()

def create_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS main_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sub_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (main_category_id) REFERENCES main_categories(id)
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sub_category_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT CHECK(type IN ('支出', '収入', '予算')) NOT NULL,
            date TEXT NOT NULL,
            detail TEXT,
            FOREIGN KEY (sub_category_id) REFERENCES sub_categories(id)
        );     
    """)

def insert_initial_categories(cursor):
    categories = ['日常', '定期', '特別', '旅行']
    cursor.executemany("INSERT INTO main_categories (name) VALUES (?);", [(cat,) for cat in categories])

def insert_initial_sub_categories(cursor):
    sub_categories = [
        (1, '二人で遊ぶお金'), (1, '食費・消耗品'), (1, '幸華お小遣い'), (1, '大河お小遣い'),
        (2, '大河給与'), (2, '大河投資'), (2, '幸華給与'), (2, '幸華投資'), (2, '家賃'),(2, 'ガス代'), (2, '電気代'), (2, '水道代'), (2, '通信代'), (2, 'サブスクリプション'),
        (3, '贈与'), (3, '病院'), (3, '引っ越し'), (3, 'イベント'), (3, 'スイッチOTC'), 
        (4, '202308イタリア'), (4, '202312オーストラリア'),(4, '202312宇治'), (4, '202312大阪'), (4, '202403三重'), (4, '202408アメリカ'), (4, '202407京都'),
    ]
    cursor.executemany("INSERT INTO sub_categories (main_category_id, name) VALUES (?, ?);", sub_categories)

def insert_transactions_from_sheets(cursor, sh):
    input_categories = ["支出", "収入", "予算", "定期契約", "旅行", "特別支出"]
    for input_category in input_categories:
        worksheet = sh.worksheet(input_category)
        data = worksheet.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        input_type = "支出" if input_category in ["支出", "定期契約", "特別支出", "旅行"] else input_category
        for _, row in df.iterrows():
            sub_category_no = get_sub_category_no(row)
            if sub_category_no:
                cursor.execute("""
                    INSERT INTO transactions (sub_category_id, amount, type, date, detail)
                    VALUES (?, ?, ?, ?, ?);
                """, (sub_category_no, row[input_type], input_type, datetime.strptime(row['日付'], "%Y/%m/%d").strftime("%Y-%m-%d"), row.get('詳細', "")))

def get_sub_category_no(row):
    category_map = {
        "食費/消耗品": 2, "二人で遊ぶお金": 1, "幸華お小遣い": 3, "大河お小遣い": 4,
        "耐久消耗品": 2, "大河給与": 5, "大河投資": 6, "幸華給与": 7, "幸華投資": 8,
        "贈与": 15, "電気代": 11, "ガス代": 10, "水道代": 12, "通信代": 13, "サブスク": 14,
        "家賃": 9, "その他": 12, "イタリア": 18, "アメリカ": 23, "オーストラリア": 19,
        "実家": 20, "三重": 22, "京都": 24, "大阪帰省": 21, "イベント": 26, "引っ越し": 17,
        "病院": 16
    }
    return category_map.get(row["カテゴリ"], None)

def load_data(conn, sub_category_id):
    query = """
        SELECT
            transactions.id,
            transactions.sub_category_id,
            transactions.date,
            transactions.detail,
            transactions.type,
            transactions.amount
        FROM
            transactions
        WHERE sub_category_id = %s;
    """
  
    query = query % sub_category_id
        
    try:
        df = pd.read_sql(query, conn)
        conn.close()   
    except:
        return None
    return df

def get_budget_and_spent(conn):
    current_month = datetime.now(pytz.timezone('Asia/Tokyo')).strftime("%Y-%m")
    query = f"""
        SELECT
            sub_categories.name as sub_category_name,
            type,
            SUM(amount) as total
        FROM
            transactions
        JOIN
            sub_categories ON transactions.sub_category_id = sub_categories.id
        JOIN
            main_categories ON sub_categories.main_category_id = main_categories.id
        WHERE
            main_categories.name = '日常' AND
            transactions.date LIKE '{current_month}%'
        GROUP BY
            sub_category_name, type;
    """
    df = pd.read_sql(query, conn)
    budget = df[df['type'] == '予算'].groupby('sub_category_name')['total'].sum()
    spent = df[df['type'] == '支出'].groupby('sub_category_name')['total'].sum()
    conn.close()
    return spent, budget

def get_categories(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM main_categories")
    main_categories = cursor.fetchall()
    cursor.execute("SELECT id, main_category_id, name FROM sub_categories")
    sub_categories = cursor.fetchall()
    return main_categories, sub_categories

def update_data(df, changes):
    try:
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        print("changes")
        print(changes)
        if changes["edited_rows"]:
            deltas = st.session_state.inventory_table["edited_rows"]
            rows = [dict(df.iloc[i].to_dict(), **delta) for i, delta in deltas.items()]

            if rows:
                cursor.executemany("""
                    UPDATE transactions
                    SET
                        amount = :amount,
                        date = :date,
                        type = :type,
                        detail = :detail
                    WHERE id = :id
                """, rows)

        if changes["added_rows"]:
            deltas = st.session_state.inventory_table["added_rows"]
            for delta in deltas:
                if not delta :
                    st.error("空の行が追加されています。空の削除をお願いします。")
                    deltas.remove(delta)
            if deltas:
                rows = [dict(df.iloc[i].to_dict(), **delta) for i, delta in enumerate(deltas)]
                if rows:
                    cursor.executemany("""
                        INSERT INTO transactions
                            (sub_category_id, amount, type, date, detail)
                        VALUES
                            (:sub_category_id, :amount, :type, :date, :detail)
                    """, rows)

        if changes["deleted_rows"]:

            cursor.executemany("DELETE FROM transactions WHERE id = :id", [{"id": int(df.loc[i, "id"])} for i in changes["deleted_rows"]])

        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# Main script
if not exists_db_file():
    sh = get_worksheet_from_gspread_client()
    conn = connect_db()
    initialize_data(conn, sh)

with st.sidebar:
    view_category = st.selectbox(label="ページ変更", options=["追加","編集","カテゴリー追加・編集","開発者オプション"])

    conn = connect_db()
    spent, budget = get_budget_and_spent(conn)
    today = date.today()
    st.title("今月の予算進捗")
    st.markdown(f" **【{today.month}月分】** {today.month}月{today.day}日時点の使用状況：")
    for category in budget.index:
        spent_amount = spent.get(category, 0)
        budget_amount = budget[category]
        percentage = (spent_amount / budget_amount) * 100 if budget_amount > 0 else 0

        st.write(f"{category}: {spent_amount}円 / {budget_amount}円")
        st.progress(percentage / 100)

    # 定期契約の通知
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, sub_category_id, amount, date, detail, type
        FROM transactions
        WHERE sub_category_id IN (
            SELECT id FROM sub_categories WHERE main_category_id = (
                SELECT id FROM main_categories WHERE name = '定期'
            )
        )
        AND date = (
            SELECT MAX(date) FROM transactions t2 WHERE t2.detail = transactions.detail
        )
    """)
    recurring_transactions = cursor.fetchall()
    conn.close()
    if recurring_transactions:
        st.write("---")
        st.title("未入力の月額")

        transaction_to_show = []
        for transaction in recurring_transactions:
            transaction_date = datetime.strptime(transaction[3], "%Y-%m-%d").date()

            if today >= (transaction_date + relativedelta(months=1)) and today < (transaction_date + relativedelta(months=2)) and transaction[2] > 0:
                transaction_to_show.append((transaction[0], transaction[1], transaction[2], transaction_date, transaction[4] , transaction[5]))
        
        if st.toggle(f"{len(transaction_to_show)}件の未入力の月額あり"):
            for transaction in transaction_to_show:
                id = transaction[0]
                sub_category_id = transaction[1]
                amount = transaction[2]
                date_str = transaction[3].strftime("%Y/%m/%d")
                detail = transaction[4] 
                type = transaction[5]

                st.write(f"● {detail}  (前回入力 {date_str})")
                new_amount = st.number_input(f"{type}額", key=f"add_amount_data_{id} ", value=amount)
                new_date = st.date_input(f"今回の日付", key=f"add_date_data_{id} ",value=today)
                if st.button(f"{detail}のデータを追加", key=f"add_data_{id}"):
                    conn = connect_db()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO transactions (sub_category_id, amount, type, date, detail)
                        VALUES (?, ?, ?, ?, ?);
                    """, (sub_category_id, new_amount, type, new_date.strftime("%Y-%m-%d"), detail))
                    conn.commit()
                    conn.close()
                    st.success(f"{detail}のデータが追加されました")
                    st.rerun()
                st.write("---")

today = date.today()
conn = connect_db()
main_categories, sub_categories = get_categories(conn)
main_category = st.selectbox("カテゴリ", [cat[1] for cat in main_categories])
main_category_id = next(cat[0] for cat in main_categories if cat[1] == main_category)

def backup_data_to_spreadsheet(conn):
    cursor = conn.cursor()

    # cursor.execute("CREATE TABLE IF NOT EXISTS backup_time (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT);")
    backup_time = cursor.execute("SELECT * FROM backup_time ORDER BY time DESC LIMIT 1").fetchone()
    # backup_time_str = backup_time.fetchall() #ORDER BY time DESC LIMIT 1
    st.write(backup_time[1])

    if (not backup_time) or (datetime.now(pytz.timezone('Asia/Tokyo')) - datetime.strptime(backup_time[1], "%Y/%m/%d %H:%M:%S") >= timedelta(days=1)):
        cursor.execute("INSERT INTO backup_time (time) VALUES (?)", [datetime.now(pytz.timezone('Asia/Tokyo')).strftime("%Y/%m/%d %H:%M:%S")])
        conn.commit()

        sh = get_worksheet_from_gspread_client()
        tables = ["main_categories", "sub_categories", "transactions", "backup_time"]
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            data = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            df = pd.DataFrame(data, columns=columns)
        
            try:
                worksheet = sh.worksheet(table)
                worksheet.clear()
            except gspread.exceptions.WorksheetNotFound:
                worksheet = sh.add_worksheet(title=table, rows=df.shape[0] + 1, cols=df.shape[1])
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())

        conn.close()

backup_data_to_spreadsheet(conn)

if view_category == "追加":
    sub_category = st.selectbox("サブカテゴリ", [sub[2] for sub in sub_categories if sub[1] == main_category_id])
    sub_category_id = next(sub[0] for sub in sub_categories if sub[2] == sub_category)

    selected_date = st.date_input("日付")
    input_type = st.selectbox("種別", ["支出", "収入", "予算"])
    detail = st.text_input("詳細")
    expense = st.number_input("支出額", min_value=0)

    if st.button("データを追加"):
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (sub_category_id, amount, type, date, detail)
            VALUES (?, ?, ?, ?, ?);
        """, (sub_category_id, expense, input_type, selected_date.strftime("%Y-%m-%d"), detail))
        conn.commit()
        conn.close()
        st.success("データが追加されました")

if view_category == "編集":
    sub_category = st.selectbox("サブカテゴリ", [sub[2] for sub in sub_categories if sub[1] == main_category_id])
    sub_category_id = next(sub[0] for sub in sub_categories if sub[2] == sub_category)
    conn = connect_db()
    df = load_data(conn, sub_category_id)
    min_date = datetime.strptime(df['date'].min(), "%Y-%m-%d")
    max_date = datetime.strptime(df['date'].max(), "%Y-%m-%d")
    if min_date < max_date:
        start_date, end_date = st.slider(
            "期間を選択",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="YYYY-MM-DD"
        )
    else:
        start_date = end_date = min_date
    # col1, col2 = st.columns(2)
    # with col1:
    #     start_date = st.date_input("開始日", min_date, min_value=min_date, max_value=max_date)
    # with col2:
    #     end_date = st.date_input("終了日", max_date, min_value=min_date, max_value=max_date)
    df = df[(df['date'] >= start_date.strftime("%Y-%m-%d")) & (df['date'] <= end_date.strftime("%Y-%m-%d"))]
    df = df.reset_index(drop=True)

    edited_df = st.data_editor(
        df.drop(columns=["sub_category_id"]),
        disabled=["id"],
        num_rows="dynamic",
        column_config={
            "amount": st.column_config.NumberColumn(format="¥%f"),
        },
        key="inventory_table",
    )

    has_uncommitted_changes = any(len(v) for v in st.session_state.inventory_table.values())

    st.button(
        "Commit changes",
        type="primary",
        disabled=not has_uncommitted_changes,
        on_click=update_data,
        args=(df, st.session_state.inventory_table),
    )

if view_category == "カテゴリー追加・編集":
    conn = connect_db()
    sub_category_options = [sub[2] for sub in sub_categories if sub[1] == main_category_id] + ["新規カテゴリ"]
    selected_sub_category = st.selectbox("小カテゴリを選択", sub_category_options)

    if selected_sub_category == "新規カテゴリ":
        new_sub_category = st.text_input("新しい小カテゴリ名")
        if st.button("小カテゴリを追加"):
            cursor = conn.cursor()
            cursor.execute("INSERT INTO sub_categories (main_category_id, name) VALUES (?, ?);", (main_category_id, new_sub_category))
            conn.commit()
            conn.close()    
            st.success("小カテゴリが追加されました")
    else:
        new_sub_category_name = st.text_input("リネームする小カテゴリ名", value=selected_sub_category)
        if st.button("小カテゴリをリネーム"):
            cursor = conn.cursor()
            cursor.execute("UPDATE sub_categories SET name = ? WHERE main_category_id = ? AND name = ?;", (new_sub_category_name, main_category_id, selected_sub_category))
            conn.commit()
            conn.close()    
            st.success("小カテゴリがリネームされました")

if view_category == "開発者オプション":
    if st.button("DBをダウンロード"):
        with open(DB_FILENAME, "rb") as file:
            btn = st.download_button(
                label="Download DB",
                data=file,
                file_name="kakeibo_backup.db",
                mime="application/octet-stream"
            )
    
    if st.button("Spreadsheetから同期"):
        if st.button("本当に同期しますか？DBのデータが上書きされます"):
            sh = get_worksheet_from_gspread_client()
            conn = connect_db()
            cursor = conn.cursor()

            tables = ["main_categories", "sub_categories", "transactions", "backup_time"]
            for table in tables:
                cursor.execute(f"SELECT * FROM {table}")
                data = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                df = pd.DataFrame(data, columns=columns)
                
                try:
                    worksheet = sh.worksheet(table)
                    data = worksheet.get_all_values()
                    df = pd.DataFrame(data[1:], columns=data[0])
                    df.to_sql(table, conn, if_exists="replace", index=False)

                except gspread.exceptions.WorksheetNotFound:
                    st.warning(f"Worksheet {table} not found. Created a new one.")
            
            conn.close()
            st.success("Spreadsheetから同期されました")
    # st.write("---")
    # st.title("可視化ツールの実験")
    # conn = connect_db()
    # df = load_data(conn, sub_category_id)
    # if df is not None and not df.empty:
    #     # PyGWalkerを使用してHTMLを生成する
    #     pyg_html = pyg.walk(df).to_html()

    #     # 生成したHTMLをStreamlitアプリケーションに埋め込む
    #     components.html(pyg_html, height=1000, scrolling=True)
    # else:
    #     st.warning("表示するデータがありません")

