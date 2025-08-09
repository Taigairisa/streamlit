from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import pytz
import pandas as pd
import streamlit as st

from sqlalchemy import text
from kakeibo.db import connect_db, get_budget_and_spent_of_month


def render_sidebar():
    view_category = st.sidebar.selectbox(
        label="ページ変更",
        options=["追加", "編集", "カテゴリー追加・編集", "グラフ", "開発者オプション"],
    )

    # 予算進捗
    # 月選択と予算進捗
    months = [
        (datetime.now(pytz.timezone('Asia/Tokyo')) - relativedelta(months=i)).strftime("%Y-%m")
        for i in range(12)
    ]
    selected_month = st.sidebar.selectbox("予実管理する月を選択", months, index=0, key="select_month")
    spent, budget, _ = get_budget_and_spent_of_month(selected_month)
    today = date.today()
    st.sidebar.title("今月の予算進捗")
    st.sidebar.markdown(f" **【{selected_month}月分】** {today.month}月{today.day}日時点の使用状況：")
    for category in budget.index:
        spent_amount = spent.get(category, 0)
        budget_amount = budget[category]
        percentage = (spent_amount / budget_amount) * 100 if budget_amount > 0 else 0
        percentage = percentage if percentage <= 100 else 100
        st.sidebar.write(f"{category}: {spent_amount}円 / {budget_amount}円")
        st.sidebar.progress(percentage / 100)

    # 贈与見える化
    st.sidebar.title("贈与見える化")
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
    GROUP BY detail, type;
    """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    if df.empty:
        st.sidebar.warning("贈与に関するデータがありません。")
    else:
        gifts = df[df['type'] == '収入'].set_index('detail')['total']
        returns = df[df['type'] == '支出'].set_index('detail')['total']
        for gift in gifts.index:
            gift_amount = gifts[gift]
            return_amount = sum(amount for detail, amount in returns.items() if gift in detail)
            percentage = (return_amount / gift_amount) * 100 if gift_amount > 0 else 0
            percentage = percentage if percentage <= 100 else 100
            st.sidebar.write(f"贈与: {gift}")
            st.sidebar.write(f"返礼: {return_amount}円 / {gift_amount}円")
            st.sidebar.progress(percentage / 100)

    # 定期契約の通知
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
        AND date = (
            SELECT MAX(date) FROM transactions t2 WHERE t2.detail = transactions.detail
        )
        """
    )
    with engine.connect() as conn:
        recurring_transactions = conn.execute(sql).fetchall()
    if recurring_transactions:
        st.sidebar.write("---")
        st.sidebar.title("未入力の月額")
        try:
            transaction_to_show = []
            today = date.today()
            for transaction in recurring_transactions:
                transaction_date = datetime.strptime(transaction[3], "%Y-%m-%d").date()
                if today >= (transaction_date + relativedelta(months=1)) and today < (transaction_date + relativedelta(months=2)) and transaction[2] > 0:
                    transaction_to_show.append((transaction[0], transaction[1], transaction[2], transaction_date, transaction[4], transaction[5]))

            if st.sidebar.toggle(f"{len(transaction_to_show)}件の未入力の月額あり"):
                for transaction in transaction_to_show:
                    id = transaction[0]
                    sub_category_id = transaction[1]
                    amount = transaction[2]
                    date_str = transaction[3].strftime("%Y/%m/%d")
                    detail = transaction[4]
                    type_ = transaction[5]
                    st.sidebar.write(f"● {detail}  (前回入力 {date_str})")
                    new_amount = st.sidebar.number_input(f"{type_}額", key=f"add_amount_data_{id} ", value=amount)
                    new_date = st.sidebar.date_input("今回の日付", key=f"add_date_data_{id} ", value=today)
                    if st.sidebar.button(f"{detail}のデータを追加", key=f"add_data_{id}"):
                        with engine.begin() as conn:
                            conn.execute(
                                text(
                                    """
                                    INSERT INTO transactions (sub_category_id, amount, type, date, detail)
                                    VALUES (:sid, :amount, :type, :date, :detail)
                                    """
                                ),
                                {
                                    "sid": sub_category_id,
                                    "amount": new_amount,
                                    "type": type_,
                                    "date": new_date.strftime("%Y-%m-%d"),
                                    "detail": detail,
                                },
                            )
                        st.sidebar.success(f"{detail}のデータが追加されました")
                        st.rerun()
                    st.sidebar.write("---")
        except Exception as e:
            st.sidebar.error(f"An error occurred: {str(e)}")

    return view_category
