import os
from pathlib import Path
import shutil
from datetime import datetime
import pandas as pd
import pytz
import streamlit as st
from sqlalchemy import create_engine, text

# Runtime DB settings
# Prefer /data in Docker/Fly. Allow override via env var and fallback in restricted envs.
_default_data_dir = os.environ.get("KAKEIBO_DATA_DIR", "/data")
RUNTIME_DB_DIR = Path(_default_data_dir)
try:
    RUNTIME_DB_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    # Fallback to a repo-local dir when /data is not writable (e.g. CI/sandbox)
    RUNTIME_DB_DIR = Path(__file__).resolve().parent.parent / "runtime-data"
    RUNTIME_DB_DIR.mkdir(parents=True, exist_ok=True)
DB_FILENAME = RUNTIME_DB_DIR / "kakeibo.db"

# Seed copy on first run (fallback for non-Docker runs)
SEED_DB = Path(__file__).resolve().parent.parent / "data" / "kakeibo.db"
if not DB_FILENAME.exists() and SEED_DB.exists():
    shutil.copy2(SEED_DB, DB_FILENAME)


# Global SQLAlchemy engine
ENGINE = create_engine(f"sqlite:///{DB_FILENAME}", future=True)


def exists_db_file() -> bool:
    return DB_FILENAME.exists()


def connect_db():
    """Return SQLAlchemy engine for compatibility with existing callers."""
    return ENGINE


def load_data(sub_category_id: int):
    sql = text(
        """
        SELECT id, sub_category_id, date, detail, type, amount
        FROM transactions
        WHERE sub_category_id = :sid
        """
    )
    try:
        with ENGINE.connect() as conn:
            df = pd.read_sql(sql, conn, params={"sid": sub_category_id})
    except Exception:
        return None
    return df


def get_budget_and_spent_of_month(month: str):
    sql = text(
        """
        SELECT
            sub_categories.name as sub_category_name,
            transactions.type as type,
            SUM(transactions.amount) as total
        FROM transactions
        JOIN sub_categories ON transactions.sub_category_id = sub_categories.id
        JOIN main_categories ON sub_categories.main_category_id = main_categories.id
        WHERE main_categories.name = '日常'
          AND transactions.date LIKE :month_like
        GROUP BY sub_category_name, type
        """
    )
    with ENGINE.connect() as conn:
        df = pd.read_sql(sql, conn, params={"month_like": f"{month}%"})
    budget = df[df['type'] == '予算'].groupby('sub_category_name')['total'].sum()
    spent = df[df['type'] == '支出'].groupby('sub_category_name')['total'].sum()
    return spent, budget, df


def get_categories(engine=None):
    engine = engine or ENGINE
    with engine.connect() as conn:
        mains = conn.execute(text("SELECT id, name FROM main_categories")).fetchall()
        subs = conn.execute(text("SELECT id, main_category_id, name FROM sub_categories")).fetchall()
    # Convert to list of tuples for UI compatibility
    main_categories = [(m[0], m[1]) for m in mains]
    sub_categories = [(s[0], s[1], s[2]) for s in subs]
    return main_categories, sub_categories


def update_data(df, changes):
    try:
        with ENGINE.begin() as conn:
            if changes["edited_rows"]:
                deltas = st.session_state.inventory_table["edited_rows"]
                rows = [dict(df.iloc[i].to_dict(), **delta) for i, delta in deltas.items()]
                if rows:
                    conn.execute(
                        text(
                            """
                            UPDATE transactions
                            SET amount = :amount,
                                date = :date,
                                type = :type,
                                detail = :detail
                            WHERE id = :id
                            """
                        ),
                        rows,
                    )

            if changes["added_rows"]:
                deltas = st.session_state.inventory_table["added_rows"]
                for delta in list(deltas):
                    if not delta:
                        st.error("空の行が追加されています。空の削除をお願いします。")
                        deltas.remove(delta)
                if deltas:
                    rows = [dict(df.iloc[i].to_dict(), **delta) for i, delta in enumerate(deltas)]
                    if rows:
                        conn.execute(
                            text(
                                """
                                INSERT INTO transactions (sub_category_id, amount, type, date, detail)
                                VALUES (:sub_category_id, :amount, :type, :date, :detail)
                                """
                            ),
                            rows,
                        )

            if changes["deleted_rows"]:
                rows = [{"id": int(df.loc[i, "id"])} for i in changes["deleted_rows"]]
                if rows:
                    conn.execute(text("DELETE FROM transactions WHERE id = :id"), rows)
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")


def get_monthly_summary():
    conn = connect_db()
    sql = text(
        """
        SELECT strftime('%Y-%m', date) as month, type, SUM(amount) as total
        FROM transactions
        WHERE date >= '2023-10-01'
        GROUP BY month, type
        ORDER BY month
        """
    )
    with conn.connect() as c:
        df = pd.read_sql(sql, c)
    pivot_df = df.pivot(index='month', columns='type', values='total').fillna(0)
    # Ensure columns exist even if df is empty
    for col in ['収入', '支出']:
        if col not in pivot_df.columns:
            pivot_df[col] = 0
    pivot_df['当月収支'] = pivot_df['収入'] - pivot_df['支出']
    pivot_df['累計資産'] = pivot_df['当月収支'].cumsum()
    return pivot_df
