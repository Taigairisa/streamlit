#!/usr/bin/env python3
"""
Lightweight smoke checks for kakeibo_st.
Run: python scripts/smoke_check.py
"""
from datetime import datetime

import pandas as pd
from sqlalchemy import text

from kakeibo.db import connect_db, get_budget_and_spent_of_month, get_monthly_summary


def main() -> int:
    engine = connect_db()

    # 1) Engine/connectivity
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[OK] DB connectivity")
    except Exception as e:
        print(f"[FAIL] DB connectivity: {e}")
        return 1

    # 2) Tables exist (minimal)
    required = {"main_categories", "sub_categories", "transactions"}
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
            names = {r[0] for r in rows}
        missing = required - names
        if missing:
            print(f"[FAIL] Missing tables: {sorted(missing)}")
            return 1
        print("[OK] Required tables present")
    except Exception as e:
        print(f"[FAIL] Table check error: {e}")
        return 1

    # 3) Budget/spent aggregation (safe even with empty data)
    ym = datetime.now().strftime("%Y-%m")
    try:
        spent, budget, df = get_budget_and_spent_of_month(ym)
        assert isinstance(df, pd.DataFrame)
        print("[OK] get_budget_and_spent_of_month")
    except Exception as e:
        print(f"[FAIL] get_budget_and_spent_of_month: {e}")
        return 1

    # 4) Monthly summary (safe even with empty data)
    try:
        md = get_monthly_summary()
        assert isinstance(md, pd.DataFrame)
        print("[OK] get_monthly_summary")
    except Exception as e:
        print(f"[FAIL] get_monthly_summary: {e}")
        return 1

    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

