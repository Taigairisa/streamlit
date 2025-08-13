import os
from pathlib import Path
import shutil
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
import os

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


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == column for r in rows)


def ensure_aikotoba_schema():
    """Ensure aikotoba-based multi-tenancy schema exists and seed defaults.

    - Create aikotoba table if missing
    - Add aikotoba_id columns to users, main_categories, sub_categories, transactions
    - Seed a 'public' aikotoba and backfill NULLs
    """
    with ENGINE.begin() as conn:
        # aikotoba table
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS aikotoba (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                label TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        ))

        # add aikotoba_id to tables if missing
        for table in ("users", "main_categories", "sub_categories", "transactions"):
            if not _column_exists(conn, table, "aikotoba_id"):
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN aikotoba_id INTEGER"))

        # UI metadata columns for categories (color/icon)
        for table in ("main_categories", "sub_categories"):
            if not _column_exists(conn, table, "color"):
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN color TEXT DEFAULT '#64748b'"))
            if not _column_exists(conn, table, "icon"):
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN icon TEXT DEFAULT '💡'"))

        # seed nitome aikotoba
        nitome_code = "nitome"
        nitome_label = "ニトメ"
        conn.execute(text("INSERT OR IGNORE INTO aikotoba (code, label) VALUES (:c, :l)"), {"c": nitome_code, "l": nitome_label})
        nitome_id = conn.execute(text("SELECT id FROM aikotoba WHERE code = :c"), {"c": nitome_code}).scalar_one()

        # seed public aikotoba
        public_code = "public"
        public_label = "公開"
        conn.execute(text("INSERT OR IGNORE INTO aikotoba (code, label) VALUES (:c, :l)"), {"c": public_code, "l": public_label})
        public_id = conn.execute(text("SELECT id FROM aikotoba WHERE code = :c"), {"c": public_code}).scalar_one()

        # backfill NULL aikotoba_id with nitome (for existing data)
        for table in ("users", "main_categories", "sub_categories", "transactions"):
            conn.execute(text(f"UPDATE {table} SET aikotoba_id = :did WHERE aikotoba_id IS NULL"), {"did": nitome_id})

        # Track author and timestamp on transactions for activity insights
        if not _column_exists(conn, "transactions", "created_by"):
            conn.execute(text("ALTER TABLE transactions ADD COLUMN created_by TEXT"))
        if not _column_exists(conn, "transactions", "created_at"):
            conn.execute(text("ALTER TABLE transactions ADD COLUMN created_at TEXT NOT NULL DEFAULT (datetime('now'))"))

        # Helpful indexes for activity queries
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_transactions_aid_created_by_id ON transactions(aikotoba_id, created_by, id DESC)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_transactions_aid_id ON transactions(aikotoba_id, id DESC)"))
        except Exception:
            pass

        # invites/events creation removed (rollback of TASK-005)


def get_aikotoba_id(code: str) -> int:
    """Return ID of a specific aikotoba code."""
    with ENGINE.begin() as conn:
        conn.execute(text("INSERT OR IGNORE INTO aikotoba (code, label) VALUES (:c, :l)"), {"c": code, "l": code})
        aid = conn.execute(text("SELECT id FROM aikotoba WHERE code = :c"), {"c": code}).scalar_one()
        return aid


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


def get_budget_and_spent_of_month(month: str, aikotoba_id: int):
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
          AND transactions.aikotoba_id = :aid
        GROUP BY sub_category_name, type
        """
    )
    with ENGINE.connect() as conn:
        df = pd.read_sql(sql, conn, params={"month_like": f"{month}%", "aid": aikotoba_id})
    budget = df[df['type'] == '予算'].groupby('sub_category_name')['total'].sum()
    spent = df[df['type'] == '支出'].groupby('sub_category_name')['total'].sum()
    return spent, budget, df


def get_categories(engine=None, aikotoba_id: int | None = None):
    engine = engine or ENGINE
    where = ""
    params = {}
    if aikotoba_id is not None:
        where = " WHERE aikotoba_id = :aid"
        params = {"aid": aikotoba_id}
    with engine.connect() as conn:
        mains = conn.execute(text(f"SELECT id, name FROM main_categories{where}"), params).fetchall()
        subs = conn.execute(text(f"SELECT id, main_category_id, name FROM sub_categories{where}"), params).fetchall()
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


def get_monthly_summary(aikotoba_id: int | None = None):
    conn = connect_db()
    sql = text(
        """
        SELECT strftime('%Y-%m', date) as month, type, SUM(amount) as total
        FROM transactions
        WHERE date >= '2023-10-01' {aikotoba_clause}
        GROUP BY month, type
        ORDER BY month
        """
    )
    params = {}
    aikotoba_clause = ""
    if aikotoba_id is not None:
        aikotoba_clause = "AND aikotoba_id = :aid"
        params["aid"] = aikotoba_id
    q = text(sql.text.format(aikotoba_clause=aikotoba_clause))
    with conn.connect() as c:
        df = pd.read_sql(q, c, params=params)
    pivot_df = df.pivot(index='month', columns='type', values='total').fillna(0)
    # Ensure columns exist even if df is empty
    for col in ['収入', '支出']:
        if col not in pivot_df.columns:
            pivot_df[col] = 0
    pivot_df['当月収支'] = pivot_df['収入'] - pivot_df['支出']
    pivot_df['累計資産'] = pivot_df['当月収支'].cumsum()
    # Altair expects fields as columns, not index. Also use a real datetime for temporal axis.
    pivot_df = pivot_df.reset_index()
    if not pivot_df.empty:
        try:
            pivot_df['month'] = pd.to_datetime(pivot_df['month'].astype(str) + '-01', format='%Y-%m-%d')
        except Exception:
            # Fallback: let pandas infer
            pivot_df['month'] = pd.to_datetime(pivot_df['month'], errors='coerce')
    return pivot_df


def get_transaction_by_id(transaction_id: int):
    sql = text(
        """
        SELECT
            t.id, t.sub_category_id, t.amount, t.type, t.date, t.detail,
            sc.main_category_id
        FROM transactions t
        JOIN sub_categories sc ON t.sub_category_id = sc.id
        WHERE t.id = :id
        """
    )
    with ENGINE.connect() as conn:
        result = conn.execute(sql, {"id": transaction_id}).fetchone()
    return result

def get_gifts_summary(aikotoba_id: int | None = None):
    engine = connect_db()
    query = text(
        """
    SELECT 
        detail,
        type,
        SUM(amount) as total
    FROM transactions
    WHERE type IN ('収入', '支出') AND sub_category_id IN (
        SELECT id FROM sub_categories WHERE name = '贈与'
    )
    {aikotoba_clause}
    GROUP BY detail, type;
    """
    )
    params = {}
    aikotoba_clause = ""
    if aikotoba_id is not None:
        aikotoba_clause = "AND aikotoba_id = :aid"
        params["aid"] = aikotoba_id
    q = text(query.text.format(aikotoba_clause=aikotoba_clause))
    with engine.connect() as conn:
        df = pd.read_sql(q, conn, params=params)
    return df

def get_unentered_recurring_transactions(aikotoba_id: int | None = None):
    engine = connect_db()
    sql = text(
        """
        SELECT id, sub_category_id, amount, date, detail, type
        FROM transactions
        WHERE sub_category_id IN (
            SELECT id FROM sub_categories WHERE main_category_id = (
                SELECT id FROM main_categories WHERE name = '定期'
            )
        )
        {aikotoba_clause}
        AND date = (
            SELECT MAX(date) FROM transactions t2 WHERE t2.detail = transactions.detail
        )
        """
    )
    params = {}
    aikotoba_clause = ""
    if aikotoba_id is not None:
        aikotoba_clause = "AND aikotoba_id = :aid"
        params["aid"] = aikotoba_id
    q = text(sql.text.format(aikotoba_clause=aikotoba_clause))
    with engine.connect() as conn:
        recurring_transactions = conn.execute(q, params).fetchall()
    return recurring_transactions


def add_sub_category(main_category_id: int, name: str):
    with ENGINE.begin() as conn:
        # inherit aikotoba_id from main category
        aid = conn.execute(text("SELECT aikotoba_id FROM main_categories WHERE id = :mid"), {"mid": main_category_id}).scalar()
        conn.execute(
            text("INSERT INTO sub_categories (main_category_id, name, aikotoba_id) VALUES (:mid, :name, :aid)"),
            {"mid": main_category_id, "name": name, "aid": aid},
        )

def rename_sub_category(sub_category_id: int, new_name: str):
    with ENGINE.begin() as conn:
        conn.execute(
            text("UPDATE sub_categories SET name = :new_name WHERE id = :id"),
            {"new_name": new_name, "id": sub_category_id},
        )

def delete_sub_category(sub_category_id: int):
    with ENGINE.begin() as conn:
        conn.execute(
            text("DELETE FROM sub_categories WHERE id = :id"),
            {"id": sub_category_id},
        )

def get_sub_category_by_id(sub_category_id: int):
    sql = text("SELECT id, main_category_id, name FROM sub_categories WHERE id = :id")
    with ENGINE.connect() as conn:
        result = conn.execute(sql, {"id": sub_category_id}).fetchone()
    return result
