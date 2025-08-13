from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
from sqlalchemy import text
from datetime import datetime
from dateutil.relativedelta import relativedelta


@dataclass
class InsightCard:
    text: str
    category: str
    rate: int
    diff: int
    sub_category_id: int


def delta_card(name: str, cur: int, prev: int, sub_category_id: int, label: str, threshold: int = 10) -> InsightCard | None:
    if prev == 0:
        return None
    rate = int((cur - prev) / prev * 100)
    if abs(rate) < threshold:
        return None
    sign = "+" if rate > 0 else ""
    amount = cur - prev
    sign_amt = "+" if amount > 0 else ("-" if amount < 0 else "")
    text = f"{label}: {name} {sign}{rate}%（{sign_amt}¥{abs(amount):,}）"
    return InsightCard(text=text, category=name, rate=rate, diff=amount, sub_category_id=sub_category_id)


def _month_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _sum_by_sub_category(conn, ym: str, aikotoba_id: int) -> Dict[int, Dict[str, int | str]]:
    q = text(
        """
        SELECT sc.id as sub_category_id, sc.name as name, COALESCE(SUM(t.amount),0) as total
          FROM transactions t
          JOIN sub_categories sc ON t.sub_category_id = sc.id
         WHERE t.type = '支出'
           AND strftime('%Y-%m', t.date) = :ym
           AND t.aikotoba_id = :aid
         GROUP BY sc.id, sc.name
        """
    )
    rows = conn.execute(q, {"ym": ym, "aid": aikotoba_id}).mappings().all()
    return {int(r["sub_category_id"]): {"name": r["name"], "total": int(r["total"])} for r in rows}


def build_insights_cards(engine, ym: str, aikotoba_id: int, threshold: int = 10) -> List[InsightCard]:
    now_dt = datetime.strptime(ym + "-01", "%Y-%m-%d")
    last_month = _month_str(now_dt - relativedelta(months=1))
    last_year_same = _month_str(now_dt - relativedelta(years=1))
    with engine.connect() as conn:
        cur = _sum_by_sub_category(conn, ym, aikotoba_id)
        prev = _sum_by_sub_category(conn, last_month, aikotoba_id)
        yoy = _sum_by_sub_category(conn, last_year_same, aikotoba_id)

    cards: List[InsightCard] = []
    for sid, cur_row in cur.items():
        name = str(cur_row["name"])
        cur_total = int(cur_row["total"])
        if sid in prev:
            label = f"先月比（{last_month} vs {ym}）"
            c = delta_card(name, cur_total, int(prev[sid]["total"]), sid, label, threshold)
            if c:
                cards.append(c)
        if sid in yoy:
            label2 = f"前年比（{last_year_same} vs {ym}）"
            c2 = delta_card(name, cur_total, int(yoy[sid]["total"]), sid, label2, threshold)
            if c2:
                cards.append(c2)
    # Sort by absolute diff desc, take top 6 for brevity
    cards.sort(key=lambda x: abs(x.diff), reverse=True)
    return cards[:6]
