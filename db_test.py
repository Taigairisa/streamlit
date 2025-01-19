from pathlib import Path
import sqlite3
from datetime import datetime
import streamlit as st
import altair as alt
import pandas as pd
from collections import defaultdict
from google.oauth2 import service_account
import gspread
import re

SHEET_KEY = st.secrets.SP_SHEET_KEY.key
SPREADSHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT = st.secrets["gcp_service_account"]

def get_worksheet_from_gspread_client():
    credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT, scopes=SPREADSHEET_SCOPES)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_KEY)
    return sh

sh = get_worksheet_from_gspread_client()

def connect_db():
    """Connects to the sqlite database."""

    DB_FILENAME = Path(__file__).parent / "kakeibo.db" #"inventory.db"
    db_already_exists = DB_FILENAME.exists()

    conn = sqlite3.connect(DB_FILENAME)
    db_was_just_created = not db_already_exists

    return conn, db_was_just_created


conn, db_was_just_created = connect_db()

def initialize_data(conn):
    """Initializes the inventory table with some data."""
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS main_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sub_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (main_category_id) REFERENCES main_categories(id)
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sub_category_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT CHECK(type IN ('支出', '収入', '予算')) NOT NULL,
            date TEXT NOT NULL,
            detail TEXT,
            FOREIGN KEY (sub_category_id) REFERENCES sub_categories(id)
        );     
        """
    )
       
    # カテゴリーテーブルの作成
    cursor.execute("""INSERT INTO main_categories (name) VALUES ('日常');""")
    cursor.execute("""INSERT INTO main_categories (name) VALUES ('定期');""")
    cursor.execute("""INSERT INTO main_categories (name) VALUES ('特別');""")
    cursor.execute("""INSERT INTO main_categories (name) VALUES ('旅行');""")

    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (1, '二人で遊ぶお金');""") #1
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (1, '食費・消耗品');""") #2
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (1, '幸華お小遣い');""") #3
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (1, '大河お小遣い');""") #4
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (2, '大河給与');""") #5
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (2, '大河投資');""") #6
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (2, '幸華給与');""") #7
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (2, '幸華投資');""") #8
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (2, '家賃');""") #9
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (2, 'ガス代');""") #10
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (2, '電気代');""") #11
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (2, '水道代');""") #12
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (2, '通信代');""") #13
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (2, 'サブスクリプション');""") #14
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (3, '贈与');""") #15
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (3, '病院');""") #16
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (3, '引っ越し');""") #17
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (4, '202308イタリア');""") #18
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (4, '202312オーストラリア');""") #19
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (4, '202312宇治');""") #20
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (4, '202312大阪');""") #21
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (4, '202403三重');""") #22
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (4, '202408アメリカ');""") #23
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (4, '202407京都');""") #24
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (4, '202407京都');""") #25
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (3, 'イベント');""") #26
    cursor.execute("""INSERT INTO sub_categories (main_category_id, name) VALUES (3, 'スイッチOTC');""") #27

    input_categories = ["支出","収入","予算","定期契約","旅行","特別支出"]
    for input_category in input_categories:

        worksheet = sh.worksheet(input_category)

        data = worksheet.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        if input_category in ["支出", "定期契約", "特別支出", "旅行"]:
            input_type = "支出"
        elif input_category == "収入":
            input_type = "収入"
        elif input_category == "予算":
            input_type = "予算"

        for index, row in df.iterrows():
            if row["カテゴリ"] == "食費/消耗品":
                sub_category_no = 2
            elif row["カテゴリ"] == "二人で遊ぶお金":
                sub_category_no = 1
            elif row["カテゴリ"] == "幸華お小遣い":
                sub_category_no = 3
            elif row["カテゴリ"] == "大河お小遣い":
                sub_category_no = 4
            elif row["カテゴリ"] == "耐久消耗品":
                sub_category_no = 2
            elif row["カテゴリ"] == "大河給与":
                sub_category_no = 5
            elif row["カテゴリ"] == "大河投資":
                sub_category_no = 6
            elif row["カテゴリ"] == "幸華給与":
                sub_category_no = 7
            elif row["カテゴリ"] == "幸華投資":
                sub_category_no = 8
            elif row["カテゴリ"] == "贈与":
                sub_category_no = 15
            elif row["カテゴリ"] == "電気代":
                sub_category_no = 11
            elif row["カテゴリ"] == "ガス代":
                sub_category_no = 10
            elif row["カテゴリ"] == "水道代":
                sub_category_no = 12
            elif row["カテゴリ"] == "通信代":
                sub_category_no = 13
            elif row["カテゴリ"] == "サブスク":
                sub_category_no = 14
            elif row["カテゴリ"] == "家賃":
                sub_category_no = 9
            elif row["カテゴリ"] == "その他":
                if row["詳細"] == "UNHCR":
                    sub_category_no = 14
                else:
                    sub_category_no = 12
            elif row["カテゴリ"] == "イタリア":
                sub_category_no = 18
            elif row["カテゴリ"] == "アメリカ":
                sub_category_no = 23
            elif row["カテゴリ"] == "オーストラリア":
                sub_category_no = 19
            elif row["カテゴリ"] == "実家":
                sub_category_no = 20
            elif row["カテゴリ"] == "三重":
                sub_category_no = 22
            elif row["カテゴリ"] == "京都":
                sub_category_no = 24
            elif row["カテゴリ"] == "大阪帰省":
                sub_category_no = 21
            elif row["カテゴリ"] == "イベント":
                sub_category_no = 26
            elif row["カテゴリ"] == "贈与":
                sub_category_no = 15
            elif row["カテゴリ"] == "引っ越し":
                sub_category_no = 17
            elif row["カテゴリ"] == "病院":
                sub_category_no = 16
            else:
                continue
        
            cursor.execute(
                """
                INSERT INTO transactions (sub_category_id, amount, type, date, detail)
                VALUES (?, ?, ?, ?, ?);
                """,
                (sub_category_no, row[input_type],input_type,datetime.strptime(row['日付'],"%Y/%m/%d").strftime("%Y-%m-%d"), row['詳細'] if "詳細" in row else "")
            )

    conn.commit()
    conn.close()

# Initialize data.
if db_was_just_created:
    initialize_data(conn)

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

conn, db_was_just_created = connect_db()
df = load_data(conn)

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

conn, db_was_just_created = connect_db()
spent, budget = get_budget_and_spent(conn)

for category in budget.index:
    spent_amount = spent.get(category, 0)
    budget_amount = budget[category]
    percentage = (spent_amount / budget_amount) * 100 if budget_amount > 0 else 0
    st.write(f"{category}: {spent_amount}円 / {budget_amount}円")
    st.progress(percentage / 100)

# カテゴリとサブカテゴリの選択肢を取得
def get_categories(conn):
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM main_categories")
    main_categories = cursor.fetchall()
    cursor.execute("SELECT id, main_category_id, name FROM sub_categories")
    sub_categories = cursor.fetchall()
    return main_categories, sub_categories

conn, db_was_just_created = connect_db()
main_categories, sub_categories = get_categories(conn)

# Streamlit UI
st.title("データベースにデータを追加")

# 日付入力
date = st.date_input("日付", datetime.now())

# カテゴリ選択
main_category = st.selectbox("カテゴリ", [cat[1] for cat in main_categories])
main_category_id = next(cat[0] for cat in main_categories if cat[1] == main_category)

# サブカテゴリ選択
sub_category = st.selectbox("サブカテゴリ", [sub[2] for sub in sub_categories if sub[1] == main_category_id])
sub_category_id = next(sub[0] for sub in sub_categories if sub[2] == sub_category)

# 詳細入力
detail = st.text_input("詳細")

# 支出額入力
expense = st.number_input("支出額", min_value=0)


def update_data(conn, df, changes):
    """Updates the inventory data in the database."""
    cursor = conn.cursor()

    if changes["edited_rows"]:
        deltas = st.session_state.inventory_table["edited_rows"]
        rows = []

        for i, delta in deltas.items():
            row_dict = df.iloc[i].to_dict()
            row_dict.update(delta)
            rows.append(row_dict)

        cursor.executemany(
            """
            UPDATE inventory
            SET
                item_name = :item_name,
                price = :price,
                units_sold = :units_sold,
                units_left = :units_left,
                cost_price = :cost_price,
                reorder_point = :reorder_point,
                description = :description
            WHERE id = :id
            """,
            rows,
        )

    if changes["added_rows"]:
        cursor.executemany(
            """
            INSERT INTO inventory
                (id, item_name, price, units_sold, units_left, cost_price, reorder_point, description)
            VALUES
                (:id, :item_name, :price, :units_sold, :units_left, :cost_price, :reorder_point, :description)
            """,
            (defaultdict(lambda: None, row) for row in changes["added_rows"]),
        )

    if changes["deleted_rows"]:
        cursor.executemany(
            "DELETE FROM inventory WHERE id = :id",
            ({"id": int(df.loc[i, "id"])} for i in changes["deleted_rows"]),
        )

    conn.commit()


# Load data from database
df = load_data(conn)
# 正規表現パターンを定義
date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

edited_df = st.data_editor(
    df,
    disabled=["id"],  # Don't allow editing the 'id' column.
    num_rows="dynamic",  # Allow appending/deleting rows.
    column_config={
        # Show dollar sign before price columns.
        "amount": st.column_config.NumberColumn(format="¥%f"),
        # "date": st.column_config.TextColumn(
        #     validate=lambda x: bool(date_pattern.match(x)),
        #     help="YYYY-MM-DD形式で入力してください"
        # )
    },
    key="inventory_table",
)



has_uncommitted_changes = any(len(v) for v in st.session_state.inventory_table.values())

st.button(
    "Commit changes",
    type="primary",
    disabled=not has_uncommitted_changes,
    # Update data in database
    on_click=update_data,
    args=(conn, df, st.session_state.inventory_table),
)
