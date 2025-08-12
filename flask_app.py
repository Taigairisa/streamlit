import os
import secrets
import urllib.parse
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import date
from sqlalchemy import text
from kakeibo.db import connect_db, get_categories, get_transaction_by_id, add_sub_category, rename_sub_category, delete_sub_category, get_sub_category_by_id, get_monthly_summary, DB_FILENAME, get_gifts_summary, get_unentered_recurring_transactions, get_budget_and_spent_of_month
import altair as alt
import json
from flask import send_file
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import pytz
import pandas as pd

app = Flask(__name__)
# Minimal secret key for session (override via env in production)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret')

def get_sidebar_data(selected_month=None):
    # Month selection for budget progress
    months = [
        (datetime.now(pytz.timezone('Asia/Tokyo')) - relativedelta(months=i)).strftime("%Y-%m")
        for i in range(12)
    ]
    if selected_month is None:
        selected_month = months[0]

    # Budget progress
    spent, budget, _ = get_budget_and_spent_of_month(selected_month)
    budget_progress = []
    for category in budget.index:
        spent_amount = spent.get(category, 0)
        budget_amount = budget[category]
        percentage = (spent_amount / budget_amount) * 100 if budget_amount > 0 else 0
        percentage = percentage if percentage <= 100 else 100
        budget_progress.append({
            'category': category,
            'spent': spent_amount,
            'budget': budget_amount,
            'percentage': percentage
        })

    # Gift visualization
    gifts_df = get_gifts_summary()
    gift_summary = []
    if not gifts_df.empty:
        gifts = gifts_df[gifts_df['type'] == '収入'].set_index('detail')['total']
        returns = gifts_df[gifts_df['type'] == '支出'].set_index('detail')['total']
        for gift_detail in gifts.index:
            gift_amount = gifts[gift_detail]
            return_amount = sum(amount for detail, amount in returns.items() if gift_detail in detail)
            percentage = (return_amount / gift_amount) * 100 if gift_amount > 0 else 0
            percentage = percentage if percentage <= 100 else 100
            gift_summary.append({
                'detail': gift_detail,
                'gift_amount': gift_amount,
                'return_amount': return_amount,
                'percentage': percentage
            })

    # Unentered monthly amounts
    recurring_transactions = get_unentered_recurring_transactions()
    unentered_amounts = []
    today = date.today()
    for transaction in recurring_transactions:
        transaction_date = datetime.strptime(transaction.date, "%Y-%m-%d").date()
        if today >= (transaction_date + relativedelta(months=1)) and today < (transaction_date + relativedelta(months=2)) and transaction.amount > 0:
            unentered_amounts.append({
                'detail': transaction.detail,
                'last_date': transaction.date
            })

    return {
        'months': months,
        'selected_month': selected_month,
        'budget_progress': budget_progress,
        'gift_summary': gift_summary,
        'unentered_amounts': unentered_amounts
    }

@app.route('/')
def index():
    month = request.args.get('month')
    if month:
        return redirect(url_for('add', month=month))
    return redirect(url_for('add'))

@app.route('/add', methods=['GET', 'POST'])
def add():
    engine = connect_db()
    main_categories, sub_categories = get_categories(engine)

    if request.method == 'POST':
        sub_category_id = request.form['sub_category_id']
        transaction_date = request.form['date']
        transaction_type = request.form['type']
        detail = request.form['detail']
        amount = request.form['amount']

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
                    "amount": amount,
                    "type": transaction_type,
                    "date": transaction_date,
                    "detail": detail,
                },
            )
        return redirect(url_for('index'))

    return render_template(
        'add.html',
        main_categories=main_categories,
        sub_categories=sub_categories,
        today=date.today().strftime('%Y-%m-%d'),
        **get_sidebar_data(selected_month=request.args.get('month'))
    )

@app.route('/edit')
def edit():
    engine = connect_db()
    main_categories, sub_categories = get_categories(engine)

    # Get filter criteria from query parameters
    main_category_id = request.args.get('main_category_id')
    sub_category_id = request.args.get('sub_category_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Base query
    query = """
        SELECT
            t.id, t.date, t.detail, t.type, t.amount,
            sc.name as sub_category_name, mc.name as main_category_name
        FROM transactions t
        JOIN sub_categories sc ON t.sub_category_id = sc.id
        JOIN main_categories mc ON sc.main_category_id = mc.id
        WHERE 1=1
    """
    params = {}

    if main_category_id:
        query += " AND mc.id = :main_category_id"
        params['main_category_id'] = main_category_id
    if sub_category_id:
        query += " AND t.sub_category_id = :sub_category_id"
        params['sub_category_id'] = sub_category_id
    if start_date:
        query += " AND t.date >= :start_date"
        params['start_date'] = start_date
    if end_date:
        query += " AND t.date <= :end_date"
        params['end_date'] = end_date

    query += " ORDER BY t.date DESC"

    # The page now renders a spreadsheet-like editor (Tabulator) and fetches data via JSON API.
    return render_template(
        'edit_list.html',
        main_categories=main_categories,
        sub_categories=sub_categories,
        **get_sidebar_data(selected_month=request.args.get('month'))
    )


@app.get('/api/transactions')
def api_get_transactions():
    engine = connect_db()
    main_category_id = request.args.get('main_category_id')
    sub_category_id = request.args.get('sub_category_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = """
        SELECT
            t.id, t.date, t.detail, t.type, t.amount,
            t.sub_category_id,
            sc.name as sub_category_name, mc.id as main_category_id, mc.name as main_category_name
        FROM transactions t
        JOIN sub_categories sc ON t.sub_category_id = sc.id
        JOIN main_categories mc ON sc.main_category_id = mc.id
        WHERE 1=1
    """
    params = {}
    if main_category_id:
        query += " AND mc.id = :main_category_id"
        params['main_category_id'] = main_category_id
    if sub_category_id:
        query += " AND t.sub_category_id = :sub_category_id"
        params['sub_category_id'] = sub_category_id
    if start_date:
        query += " AND t.date >= :start_date"
        params['start_date'] = start_date
    if end_date:
        query += " AND t.date <= :end_date"
        params['end_date'] = end_date
    query += " ORDER BY t.date DESC, t.id DESC"

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()
        data = [dict(r) for r in rows]
    return jsonify(data)


@app.post('/api/transactions')
def api_create_transaction():
    engine = connect_db()
    payload = request.get_json(force=True, silent=True) or {}
    required = ['sub_category_id', 'date', 'type', 'amount']
    if not all(k in payload and payload[k] not in (None, '') for k in required):
        return jsonify({"error": "Missing required fields"}), 400
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO transactions (sub_category_id, amount, type, date, detail)
                VALUES (:sid, :amount, :type, :date, :detail)
                """
            ),
            {
                "sid": payload['sub_category_id'],
                "amount": payload['amount'],
                "type": payload['type'],
                "date": payload['date'],
                "detail": payload.get('detail', ''),
            },
        )
        new_id = result.lastrowid
    return jsonify({"id": new_id}), 201


@app.patch('/api/transactions/<int:transaction_id>')
def api_update_transaction(transaction_id: int):
    engine = connect_db()
    payload = request.get_json(force=True, silent=True) or {}
    allowed = {'sub_category_id', 'amount', 'type', 'date', 'detail'}
    fields = {k: payload[k] for k in allowed if k in payload}
    if not fields:
        return jsonify({"error": "No fields to update"}), 400
    set_clause = ", ".join([f"{k} = :{k}" for k in fields.keys()])
    fields['id'] = transaction_id
    with engine.begin() as conn:
        res = conn.execute(text(f"UPDATE transactions SET {set_clause} WHERE id = :id"), fields)
    return jsonify({"updated": res.rowcount})


@app.delete('/api/transactions/<int:transaction_id>')
def api_delete_transaction(transaction_id: int):
    engine = connect_db()
    with engine.begin() as conn:
        res = conn.execute(text("DELETE FROM transactions WHERE id = :id"), {"id": transaction_id})
    return jsonify({"deleted": res.rowcount})

@app.route('/dev', methods=['GET', 'POST'])
def dev_options():
    sql_result = None
    if request.method == 'POST':
        sql_query = request.form['sql_query']
        engine = connect_db()
        try:
            with engine.connect() as conn:
                # For SELECT statements
                if sql_query.strip().upper().startswith('SELECT'):
                    result = conn.execute(text(sql_query)).fetchall()
                    sql_result = "\n".join([str(row) for row in result])
                # For DML/DDL statements
                else:
                    with conn.begin(): # Use begin() for transactions
                        result = conn.execute(text(sql_query))
                        sql_result = f"Rows affected: {result.rowcount}"
        except Exception as e:
            sql_result = f"Error: {str(e)}"

    return render_template('dev_options.html', sql_result=sql_result, **get_sidebar_data(selected_month=request.args.get('month')))

@app.route('/download_db')
def download_db():
    """Download the current SQLite database file.

    This endpoint is linked from the developer options page.
    """
    try:
        # DB_FILENAME is a pathlib.Path
        if not DB_FILENAME.exists():
            return "Database file not found.", 404
        return send_file(
            DB_FILENAME,
            as_attachment=True,
            download_name='kakeibo.db',
            mimetype='application/octet-stream',
        )
    except Exception as e:
        # Keep it simple; in production we would log this.
        return f"Failed to prepare download: {str(e)}", 500


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Clear auth-related session keys and redirect to home."""
    for key in [
        'auth_user', 'user_id', 'username', 'role'
    ]:
        session.pop(key, None)
    return redirect(url_for('index'))


# ===============
# LINE OAuth
# ===============

LINE_AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
LINE_TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
LINE_PROFILE_URL = "https://api.line.me/v2/profile"


def _line_cfg():
    cid = os.environ.get("LINE_CLIENT_ID") or os.environ.get("LINE_CHANNEL_ID")
    csec = os.environ.get("LINE_CLIENT_SECRET") or os.environ.get("LINE_CHANNEL_SECRET")
    redirect_uri = os.environ.get("LINE_REDIRECT_URI")
    if not redirect_uri:
        # fallback for local dev
        # Use current host if available
        try:
            base = request.host_url.rstrip('/')
            redirect_uri = f"{base}/callback/line"
        except Exception:
            redirect_uri = "http://localhost:5000/callback/line"
    if cid and csec and redirect_uri:
        return {"client_id": cid, "client_secret": csec, "redirect_uri": redirect_uri}
    return None


def _ensure_oauth_state_table():
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        ))


def _save_state(state: str):
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO oauth_states (state) VALUES (:s)"), {"s": state})


def _is_valid_state(state: str) -> bool:
    engine = connect_db()
    with engine.connect() as conn:
        row = conn.execute(text(
            """
            SELECT 1 FROM oauth_states
             WHERE state = :s
               AND datetime(created_at) >= datetime('now','-10 minutes')
            """
        ), {"s": state}).fetchone()
    return bool(row)


def _remove_state(state: str):
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM oauth_states WHERE state = :s"), {"s": state})


def _cleanup_old_states():
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM oauth_states WHERE datetime(created_at) < datetime('now','-1 day')"))


def _ensure_users_table():
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        ))


def _user_exists(username: str) -> bool:
    engine = connect_db()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT 1 FROM users WHERE username = :u"), {"u": username}).fetchone()
    return bool(row)


def _create_user(username: str):
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (username, password) VALUES (:u, :p)"), {"u": username, "p": "external"})


@app.route('/login/line')
def login_line():
    cfg = _line_cfg()
    if not cfg:
        return "LINEログインの設定が不足しています。環境変数を設定してください。", 500
    _ensure_oauth_state_table()
    _cleanup_old_states()
    state = secrets.token_urlsafe(16)
    _save_state(state)
    params = {
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "state": state,
        "scope": "profile openid",
    }
    auth_url = f"{LINE_AUTH_URL}?{urllib.parse.urlencode(params, safe=':/')}"
    return redirect(auth_url)


@app.route('/callback/line')
def callback_line():
    cfg = _line_cfg()
    if not cfg:
        return "LINEログインの設定が不足しています。", 500
    code = request.args.get('code')
    state = request.args.get('state')
    if not code or not state or not _is_valid_state(state):
        return "不正なリクエストです（state/code）", 400
    _remove_state(state)

    # Exchange token
    try:
        token_resp = requests.post(
            LINE_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": cfg["redirect_uri"],
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
            },
            timeout=15,
        )
    except Exception as e:
        return f"トークン要求に失敗しました: {str(e)}", 500
    if token_resp.status_code != 200:
        return f"LINEログイン失敗: {token_resp.text}", 400
    token_json = token_resp.json()
    access_token = token_json.get("access_token")
    if not access_token:
        return "アクセストークン取得に失敗しました。", 400

    # Profile
    prof_resp = requests.get(LINE_PROFILE_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
    if prof_resp.status_code != 200:
        return f"プロフィール取得に失敗しました: {prof_resp.text}", 400
    profile = prof_resp.json()
    user_id = profile.get('userId')
    if not user_id:
        return "プロフィール情報に userId がありません。", 400

    _ensure_users_table()
    username = f"line:{user_id}"
    if not _user_exists(username):
        _create_user(username)
    session['auth_user'] = username
    return redirect(url_for('index'))

@app.route('/edit/<int:transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    engine = connect_db()
    transaction = get_transaction_by_id(transaction_id)

    if not transaction:
        return "Transaction not found", 404

    main_categories, all_sub_categories = get_categories(engine)

    if request.method == 'POST':
        sub_category_id = request.form['sub_category_id']
        transaction_date = request.form['date']
        transaction_type = request.form['type']
        detail = request.form['detail']
        amount = request.form['amount']

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE transactions
                    SET sub_category_id = :sub_category_id,
                        amount = :amount,
                        type = :type,
                        date = :date,
                        detail = :detail
                    WHERE id = :id
                    """
                ),
                {
                    "id": transaction_id,
                    "sub_category_id": sub_category_id,
                    "amount": amount,
                    "type": transaction_type,
                    "date": transaction_date,
                    "detail": detail,
                },
            )
        return redirect(url_for('edit'))

    return render_template(
        'edit_transaction.html',
        transaction=transaction,
        main_categories=main_categories,
        all_sub_categories=all_sub_categories,
        **get_sidebar_data(selected_month=request.args.get('month'))
    )


@app.route('/categories', methods=['GET', 'POST'])
def categories():
    engine = connect_db()
    main_categories, sub_categories = get_categories(engine)

    if request.method == 'POST':
        main_category_id = request.form['main_category_id']
        name = request.form['name']
        add_sub_category(main_category_id, name)
        return redirect(url_for('categories'))

    return render_template(
        'categories_list.html',
        main_categories=main_categories,
        sub_categories=sub_categories,
        **get_sidebar_data(selected_month=request.args.get('month'))
    )

@app.route('/categories/edit/<int:sub_category_id>', methods=['GET', 'POST'])
def edit_category(sub_category_id):
    engine = connect_db()
    sub_category = get_sub_category_by_id(sub_category_id)

    if not sub_category:
        return "Sub-category not found", 404

    # Get main category name for display
    main_category_name = ""
    for main in get_categories(engine)[0]:
        if main[0] == sub_category.main_category_id:
            main_category_name = main[1]
            break

    if request.method == 'POST':
        new_name = request.form['name']
        rename_sub_category(sub_category_id, new_name)
        return redirect(url_for('categories'))

    return render_template(
        'edit_category.html',
        sub_category=sub_category,
        main_category_name=main_category_name,
        **get_sidebar_data(selected_month=request.args.get('month'))
    )

@app.route('/categories/delete/<int:sub_category_id>', methods=['POST'])
def delete_category(sub_category_id):
    # First, delete related transactions to maintain referential integrity
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM transactions WHERE sub_category_id = :sid"),
            {"sid": sub_category_id}
        )
    # Then delete the sub-category itself
    delete_sub_category(sub_category_id)
    return redirect(url_for('categories'))

@app.route('/delete/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM transactions WHERE id = :id"),
            {"id": transaction_id}
        )
    return redirect(url_for('edit'))

@app.route('/graphs')
def graphs():
    monthly_summary_df = get_monthly_summary()

    # Month options from data
    if not monthly_summary_df.empty:
        month_options = sorted(monthly_summary_df['month'].dt.strftime('%Y-%m').unique())
    else:
        month_options = []

    # Query params for range filtering
    start_month_q = request.args.get('start_month')
    end_month_q = request.args.get('end_month')
    if month_options:
        selected_start = start_month_q if start_month_q in month_options else month_options[0]
        selected_end = end_month_q if end_month_q in month_options else month_options[-1]
        # Normalize order if reversed
        if month_options.index(selected_start) > month_options.index(selected_end):
            selected_start, selected_end = selected_end, selected_start
        start_dt = pd.to_datetime(selected_start + '-01')
        end_dt = pd.to_datetime(selected_end + '-01')
        monthly_summary_df = monthly_summary_df[(monthly_summary_df['month'] >= start_dt) & (monthly_summary_df['month'] <= end_dt)]
    else:
        selected_start = None
        selected_end = None

    # Monthly Income/Expense Chart
    monthly_chart = alt.Chart(monthly_summary_df).mark_line().encode(
        x=alt.X('month:T', axis=alt.Axis(title='月')),
        y=alt.Y('当月収支:Q', axis=alt.Axis(title='当月収支')),
        tooltip=['month:T', '当月収支:Q']
    ).properties(
        title='月次収支'
    ).interactive()

    # Cumulative Assets Chart
    cumulative_chart = alt.Chart(monthly_summary_df).mark_line().encode(
        x=alt.X('month:T', axis=alt.Axis(title='月')),
        y=alt.Y('累計資産:Q', axis=alt.Axis(title='累計資産')),
        tooltip=['month:T', '累計資産:Q']
    ).properties(
        title='累計資産推移'
    ).interactive()

    monthly_chart_json = json.dumps(monthly_chart.to_dict())
    cumulative_chart_json = json.dumps(cumulative_chart.to_dict())

    return render_template(
        'graphs.html',
        monthly_chart_json=monthly_chart_json,
        cumulative_chart_json=cumulative_chart_json,
        month_options=month_options,
        selected_start_month=selected_start,
        selected_end_month=selected_end,
        **get_sidebar_data(selected_month=request.args.get('month'))
    )

# ===== Sub-category JSON API (for categories UX) =====

@app.get('/api/sub_categories')
def api_get_sub_categories():
    engine = connect_db()
    main_category_id = request.args.get('main_category_id')
    q = request.args.get('q')
    query = """
        SELECT sc.id, sc.name as sub_name, sc.main_category_id,
               mc.name as main_name
          FROM sub_categories sc
          JOIN main_categories mc ON sc.main_category_id = mc.id
         WHERE 1 = 1
    """
    params = {}
    if main_category_id:
        query += " AND sc.main_category_id = :mid"
        params['mid'] = main_category_id
    if q:
        query += " AND (sc.name LIKE :q OR mc.name LIKE :q)"
        params['q'] = f"%{q}%"
    query += " ORDER BY mc.id ASC, sc.id ASC"
    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()
        data = [
            {
                'id': r['id'],
                'name': r['sub_name'],
                'main_category_id': r['main_category_id'],
                'main_category_name': r['main_name'],
            }
            for r in rows
        ]
    return jsonify(data)


@app.post('/api/sub_categories')
def api_create_sub_category():
    engine = connect_db()
    payload = request.get_json(force=True, silent=True) or {}
    mid = payload.get('main_category_id')
    name = payload.get('name')
    if not mid or not name:
        return jsonify({"error": "main_category_id と name は必須です"}), 400
    with engine.begin() as conn:
        res = conn.execute(text(
            "INSERT INTO sub_categories (main_category_id, name) VALUES (:mid, :name)"
        ), {"mid": mid, "name": name})
        new_id = res.lastrowid
    return jsonify({"id": new_id}), 201


@app.patch('/api/sub_categories/<int:sub_id>')
def api_update_sub_category(sub_id: int):
    engine = connect_db()
    payload = request.get_json(force=True, silent=True) or {}
    allowed = {'name', 'main_category_id'}
    fields = {k: payload[k] for k in allowed if k in payload}
    if not fields:
        return jsonify({"error": "更新対象フィールドがありません"}), 400
    set_clause = ", ".join([f"{k} = :{k}" for k in fields.keys()])
    fields['id'] = sub_id
    with engine.begin() as conn:
        r = conn.execute(text(f"UPDATE sub_categories SET {set_clause} WHERE id = :id"), fields)
    return jsonify({"updated": r.rowcount})


@app.delete('/api/sub_categories/<int:sub_id>')
def api_delete_sub_category(sub_id: int):
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM transactions WHERE sub_category_id = :sid"), {"sid": sub_id})
        r = conn.execute(text("DELETE FROM sub_categories WHERE id = :sid"), {"sid": sub_id})
    return jsonify({"deleted": r.rowcount})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
