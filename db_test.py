from pathlib import Path
import sqlite3
from datetime import datetime
import streamlit as st
import pandas as pd
from collections import defaultdict
from google.oauth2 import service_account
import gspread
import re

SHEET_KEY = st.secrets.SP_SHEET_KEY.key
SPREADSHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT = st.secrets["gcp_service_account"]
DB_FILENAME = Path(__file__).parent / "kakeibo.db"

def get_worksheet_from_gspread_client():
    credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT, scopes=SPREADSHEET_SCOPES)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    return sh

def exists_db_file():
    return DB_FILENAME.exists()

def connect_db():
    """Connects to the sqlite database."""
    conn = sqlite3.connect(DB_FILENAME)
    return conn

def initialize_data(conn, sh):
    """Initializes the inventory table with some data."""
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
        (2, '大河給与'), (2, '大河投資'), (2, '幸華給与'), (2, '幸華投資'), (2, '家賃'),
        (2, 'ガス代'), (2, '電気代'), (2, '水道代'), (2, '通信代'), (2, 'サブスクリプション'),
        (3, '贈与'), (3, '病院'), (3, '引っ越し'), (4, '202308イタリア'), (4, '202312オーストラリア'),
        (4, '202312宇治'), (4, '202312大阪'), (4, '202403三重'), (4, '202408アメリカ'), (4, '202407京都'),
        (4, '202407京都'), (3, 'イベント'), (3, 'スイッチOTC')
    ]
    cursor.executemany("INSERT INTO sub_categories (main_category_id, name) VALUES (?, ?);", sub_categories)

def insert_transactions_from_sheets(cursor, sh):
    input_categories = ["支出", "収入", "予算", "定期契約", "旅行", "特別支出"]
    for input_category in input_categories:
        worksheet = sh.worksheet(input_category)
        data = worksheet.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        input_type = get_input_type(input_category)
        for index, row in df.iterrows():
            sub_category_no = get_sub_category_no(row)
            if sub_category_no:
                cursor.execute("""
                    INSERT INTO transactions (sub_category_id, amount, type, date, detail)
                    VALUES (?, ?, ?, ?, ?);
                """, (sub_category_no, row[input_type], input_type, datetime.strptime(row['日付'], "%Y/%m/%d").strftime("%Y-%m-%d"), row.get('詳細', "")))

def get_input_type(input_category):
    if input_category in ["支出", "定期契約", "特別支出", "旅行"]:
        return "支出"
    elif input_category == "収入":
        return "収入"
    elif input_category == "予算":
        return "予算"

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

def load_data(conn):
    """Loads the inventory data from the database."""
    query = """
        SELECT
            transactions.id,
            main_categories.name AS main_category_name,
            sub_categories.name AS sub_category_name,
            transactions.date,
            transactions.detail,
            transactions.type,
            transactions.amount
        FROM
            transactions
        JOIN
            sub_categories ON transactions.sub_category_id = sub_categories.id
        JOIN
            main_categories ON sub_categories.main_category_id = main_categories.id;
    """
    try:
        df = pd.read_sql(query, conn)
        conn.close()   
    except:
        return None
    return df

def get_budget_and_spent(conn):
    """Fetches the budget and spent amounts for the current month in the '日常' category from the database."""
    current_month = datetime.now().strftime("%Y-%m")
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

        conn = sqlite3.connect(DB_FILENAME)  # 新しいデータベース接続を作成
        cursor = conn.cursor()

        if changes["edited_rows"]:
            deltas = st.session_state.inventory_table["edited_rows"]
            rows = [defaultdict(lambda: None, dict(df.iloc[i].to_dict(), **delta)) for i, delta in deltas.items()]
            for row in rows:
                if row['sub_category_id'] is None:
                    row['sub_category_id'] = 1  # 適切なデフォルト値を設定
            cursor.executemany("""
                UPDATE transactions
                SET
                    sub_category_id = :sub_category_id,
                    amount = :amount,
                    type = :type,
                    date = :date,
                    detail = :detail
                WHERE id = :id
            """, rows)

        if changes["added_rows"]:
            rows = [defaultdict(lambda: None, row) for row in changes["added_rows"]]
            for row in rows:
                if row['sub_category_id'] is None:
                    row['sub_category_id'] = 1  # 適切なデフォルト値を設定
            cursor.executemany("""
                INSERT INTO transactions
                    (sub_category_id, amount, type, date, detail)
                VALUES
                    (:sub_category_id, :amount, :type, :date, :detail)
            """, rows)

        if changes["deleted_rows"]:
            cursor.executemany("DELETE FROM transactions WHERE id = :id", ({"id": int(df.loc[i, "id"])} for i in changes["deleted_rows"]))

            conn.commit()
            conn.close()
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Main script
sh = get_worksheet_from_gspread_client()
if not exists_db_file():
    conn = connect_db()
    initialize_data(conn, sh)

conn = connect_db()
spent, budget = get_budget_and_spent(conn)

st.title("データを編集")
for category in budget.index:
    spent_amount = spent.get(category, 0)
    budget_amount = budget[category]
    percentage = (spent_amount / budget_amount) * 100 if budget_amount > 0 else 0
    st.write(f"{category}: {spent_amount}円 / {budget_amount}円")
    st.progress(percentage / 100)

conn = connect_db()
main_categories, sub_categories = get_categories(conn)

# Streamlit UI
st.title("データベースにデータを追加")
date = st.date_input("日付", datetime.now())
main_category = st.selectbox("カテゴリ", [cat[1] for cat in main_categories])
main_category_id = next(cat[0] for cat in main_categories if cat[1] == main_category)
sub_category = st.selectbox("サブカテゴリ", [sub[2] for sub in sub_categories if sub[1] == main_category_id])
sub_category_id = next(sub[0] for sub in sub_categories if sub[2] == sub_category)
input_type = st.selectbox("種別", ["支出", "収入", "予算"])
detail = st.text_input("詳細")
expense = st.number_input("支出額", min_value=0)

if st.button("データを追加"):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (sub_category_id, amount, type, date, detail)
        VALUES (?, ?, ?, ?, ?);
    """, (sub_category_id, expense, input_type, date.strftime("%Y-%m-%d"), detail))
    conn.commit()

conn = connect_db()
df = load_data(conn)

st.title("データを編集")

edited_df = st.data_editor(
    df,
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
