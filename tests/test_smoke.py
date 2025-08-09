import pandas as pd
from sqlalchemy import text

from kakeibo.db import connect_db, get_budget_and_spent_of_month, get_monthly_summary


def test_connectivity():
    engine = connect_db()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def test_tables_exist():
    engine = connect_db()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        names = {r[0] for r in rows}
    for name in ("main_categories", "sub_categories", "transactions"):
        assert name in names


def test_aggregations_dont_crash():
    # Month string for current month
    from datetime import datetime

    ym = datetime.now().strftime("%Y-%m")
    spent, budget, df = get_budget_and_spent_of_month(ym)
    assert isinstance(df, pd.DataFrame)

    md = get_monthly_summary()
    assert isinstance(md, pd.DataFrame)

