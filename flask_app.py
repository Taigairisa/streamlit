import os
import secrets
import urllib.parse
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import date
from sqlalchemy import text
from kakeibo.db import (
    connect_db,
    get_categories,
    get_transaction_by_id,
    add_sub_category,
    rename_sub_category,
    delete_sub_category,
    get_sub_category_by_id,
    get_monthly_summary,
    DB_FILENAME,
    get_gifts_summary,
    get_unentered_recurring_transactions,
    get_budget_and_spent_of_month,
    ensure_aikotoba_schema,
    get_aikotoba_id,
    get_oldest_transaction_month,
)
import json
from flask import send_file
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import pytz
# Note: Heavy libs (pandas, altair) are imported lazily in routes that need them
from utils.budget import month_context
from services.insights import build_insights_cards

app = Flask(__name__)
# Minimal secret key for session (override via env in production)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret')

# Ensure aikotoba schema at startup
try:
    ensure_aikotoba_schema()
except Exception:
    pass

def _get_current_user_aikotoba_id() -> int:
    engine = connect_db()
    public_id = get_aikotoba_id("public")
    username = session.get('auth_user')
    if not username:
        return public_id
    try:
        with engine.connect() as conn:
            aid = conn.execute(text("SELECT aikotoba_id FROM users WHERE username = :u"), {"u": username}).scalar()
            return aid if aid is not None else public_id
    except Exception:
        return public_id

def _is_api_request() -> bool:
    try:
        return request.path.startswith('/api/')
    except Exception:
        return False

def _emit_event(conn, message: str):
    aid = _get_current_user_aikotoba_id()
    conn.execute(text("INSERT INTO events (aikotoba_id, message) VALUES (:aid, :m)"), {"aid": aid, "m": message})

@app.before_request
def require_login_guard():
    # Exempt paths
    exempt_prefixes = ['/static/']
    exempt_paths = {
        '/', '/login', '/login/line', '/callback/line', '/favicon.ico'
    }
    path = request.path
    if any(path.startswith(prefix) for prefix in exempt_prefixes) or path in exempt_paths:
        return None
    # Allow health checks if any
    if path.startswith('/health'):
        return None
    # Require session
    if not session.get('auth_user'):
        # Remember where to return after login (only for non-API)
        if not _is_api_request():
            session['post_login_redirect'] = request.full_path or path
            # Avoid trailing '?' if no query
            if session['post_login_redirect'].endswith('?'):
                session['post_login_redirect'] = session['post_login_redirect'][:-1]
            return redirect(url_for('login'))
        else:
            return jsonify({"error": "Unauthorized"}), 401

def get_sidebar_data(selected_month=None):
    aid = _get_current_user_aikotoba_id()
    
    # Month selection for budget progress
    monthly_summary_df = get_monthly_summary(aikotoba_id=aid)
    if not monthly_summary_df.empty:
        months = sorted(monthly_summary_df['month'].dt.strftime('%Y-%m').unique(), reverse=True)
    else:
        months = []

    if not months:
        # Fallback if no transactions
        months = [(datetime.now(pytz.timezone('Asia/Tokyo')) - relativedelta(months=i)).strftime("%Y-%m") for i in range(12)]

    if selected_month is None:
        selected_month = months[0]

    # Budget progress
    spent, budget, _ = get_budget_and_spent_of_month(selected_month, aid)
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

    # Totals for month header
    total_spent = int(sum(spent.to_dict().values())) if hasattr(spent, 'to_dict') else int(sum(spent.values())) if isinstance(spent, dict) else 0
    total_budget = int(sum(budget.to_dict().values())) if hasattr(budget, 'to_dict') else int(sum(budget.values())) if isinstance(budget, dict) else 0
    # Determine a reference date for the selected month
    try:
        sel_year, sel_month = map(int, selected_month.split("-"))
        now = datetime.now(pytz.timezone('Asia/Tokyo')).date()
        if now.year == sel_year and now.month == sel_month:
            ref_date = now
        else:
            # Use last day of the selected month for completed months
            d = date(sel_year, sel_month, 28)
            ref_date = d + relativedelta(day=31)
    except Exception:
        ref_date = datetime.now(pytz.timezone('Asia/Tokyo')).date()
    month_ctx = month_context(total_budget, total_spent, ref_date)

    # Gift visualization
    gifts_df = get_gifts_summary(aid)
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
    recurring_transactions = get_unentered_recurring_transactions(aid)
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
        'month_label': selected_month,
        'total_budget': total_budget,
        'total_spent': total_spent,
        'month_ctx': month_ctx,
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
    aid = _get_current_user_aikotoba_id()
    main_categories, sub_categories = get_categories(engine, aikotoba_id=aid)

    if request.method == 'POST':
        sub_category_id = request.form['sub_category_id']
        transaction_date = request.form['date']
        transaction_type = request.form['type']
        detail = request.form.get('detail', '')
        raw_amount = request.form['amount']
        try:
            amount = int(''.join(ch for ch in raw_amount if (ch.isdigit() or ch == '-')) or '0')
        except Exception:
            amount = 0

        with engine.begin() as conn:
            # derive aikotoba from sub_category
            sub_aid = conn.execute(text("SELECT aikotoba_id FROM sub_categories WHERE id = :sid"), {"sid": sub_category_id}).scalar()
            if sub_aid is None:
                sub_aid = _get_current_user_aikotoba_id()
            params = {
                "sid": sub_category_id,
                "amount": amount,
                "type": transaction_type,
                "date": transaction_date,
                "detail": detail,
                "aid": sub_aid,
                "created_by": session.get('auth_user') or 'guest',
            }
            try:
                conn.execute(
                    text(
                        """
                        INSERT INTO transactions (sub_category_id, amount, type, date, detail, aikotoba_id, created_by)
                        VALUES (:sid, :amount, :type, :date, :detail, :aid, :created_by)
                        """
                    ),
                    params,
                )
            except Exception:
                # Fallback for environments where created_by column isn't available yet
                conn.execute(
                    text(
                        """
                        INSERT INTO transactions (sub_category_id, amount, type, date, detail, aikotoba_id)
                        VALUES (:sid, :amount, :type, :date, :detail, :aid)
                        """
                    ),
                    params,
                )
        return redirect(url_for('index'))

    return render_template(
        'add.html',
        main_categories=main_categories,
        sub_categories=sub_categories,
        today=date.today().strftime('%Y-%m-%d'),
        **get_sidebar_data(selected_month=request.args.get('month'))
    )

@app.route('/login')
def login():
    # Show login page; if already logged in, go to index
    if session.get('auth_user'):
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/edit')
def edit():
    engine = connect_db()
    aid = _get_current_user_aikotoba_id()
    main_categories, sub_categories = get_categories(engine, aikotoba_id=aid)

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
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int)

    base_query = """
        SELECT
            t.id, t.date, t.detail, t.type, t.amount,
            t.sub_category_id,
            sc.name as sub_category_name, sc.icon as sub_icon,
            mc.id as main_category_id, mc.name as main_category_name,
            mc.icon as main_icon
        FROM transactions t
        JOIN sub_categories sc ON t.sub_category_id = sc.id
        JOIN main_categories mc ON sc.main_category_id = mc.id
        WHERE 1=1
    """
    count_query = """
        SELECT COUNT(*)
        FROM transactions t
        JOIN sub_categories sc ON t.sub_category_id = sc.id
        JOIN main_categories mc ON sc.main_category_id = mc.id
        WHERE 1=1
    """
    params = {}
    if main_category_id:
        base_query += " AND mc.id = :main_category_id"
        count_query += " AND mc.id = :main_category_id"
        params['main_category_id'] = main_category_id
    if sub_category_id:
        base_query += " AND t.sub_category_id = :sub_category_id"
        count_query += " AND t.sub_category_id = :sub_category_id"
        params['sub_category_id'] = sub_category_id
    if start_date:
        base_query += " AND t.date >= :start_date"
        count_query += " AND t.date >= :start_date"
        params['start_date'] = start_date
    if end_date:
        base_query += " AND t.date <= :end_date"
        count_query += " AND t.date <= :end_date"
        params['end_date'] = end_date
    q = request.args.get('q') # Get the new query parameter
    if q:
        base_query += " AND t.detail LIKE :q" # Apply to detail column
        count_query += " AND t.detail LIKE :q"
        params['q'] = f"%{q}%"
    aid = _get_current_user_aikotoba_id()
    base_query += " AND t.aikotoba_id = :aid ORDER BY t.date DESC, t.id DESC"
    count_query += " AND t.aikotoba_id = :aid"

    params['aid'] = aid
    with engine.connect() as conn:
        total_count = conn.execute(text(count_query), params).scalar()

        if limit is not None:
            base_query += f" LIMIT {limit}"
        if offset is not None:
            base_query += f" OFFSET {offset}"

        rows = conn.execute(text(base_query), params).mappings().all()
        data = [dict(r) for r in rows]
    return jsonify({"items": data, "total_count": total_count})


@app.post('/api/transactions')
def api_create_transaction():
    engine = connect_db()
    payload = request.get_json(force=True, silent=True) or {}
    required = ['sub_category_id', 'date', 'type', 'amount']
    if not all(k in payload and payload[k] not in (None, '') for k in required):
        return jsonify({"error": "Missing required fields"}), 400
    with engine.begin() as conn:
        # derive aikotoba_id from sub_category; fallback to user's
        sub_aid = conn.execute(text("SELECT aikotoba_id FROM sub_categories WHERE id = :sid"), {"sid": payload['sub_category_id']}).scalar()
        if sub_aid is None:
            sub_aid = _get_current_user_aikotoba_id()
        params = {
            "sid": payload['sub_category_id'],
            "amount": payload['amount'],
            "type": payload['type'],
            "date": payload['date'],
            "detail": payload.get('detail', ''),
            "aid": sub_aid,
            "created_by": session.get('auth_user') or 'guest',
        }
        try:
            result = conn.execute(
                text(
                    """
                    INSERT INTO transactions (sub_category_id, amount, type, date, detail, aikotoba_id, created_by)
                    VALUES (:sid, :amount, :type, :date, :detail, :aid, :created_by)
                    """
                ),
                params,
            )
        except Exception:
            result = conn.execute(
                text(
                    """
                    INSERT INTO transactions (sub_category_id, amount, type, date, detail, aikotoba_id)
                    VALUES (:sid, :amount, :type, :date, :detail, :aid)
                    """
                ),
                params,
            )
        new_id = result.lastrowid
        try:
            pass
        except Exception:
            pass
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
    fields['aid'] = _get_current_user_aikotoba_id()
    with engine.begin() as conn:
        res = conn.execute(text(f"UPDATE transactions SET {set_clause} WHERE id = :id AND aikotoba_id = :aid"), fields)
        if res.rowcount:
            try:
                pass
            except Exception:
                pass
    return jsonify({"updated": res.rowcount})


@app.delete('/api/transactions/<int:transaction_id>')
def api_delete_transaction(transaction_id: int):
    engine = connect_db()
    with engine.begin() as conn:
        res = conn.execute(text("DELETE FROM transactions WHERE id = :id AND aikotoba_id = :aid"), {"id": transaction_id, "aid": _get_current_user_aikotoba_id()})
        try:
            pass
        except Exception:
            pass
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
# Aikotoba (passcode) settings
# ===============

@app.route('/aikotoba', methods=['GET'])
def aikotoba_settings():
    engine = connect_db()
    aid = _get_current_user_aikotoba_id()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT code, label FROM aikotoba WHERE id = :id"), {"id": aid}).fetchone()
    current = {"code": row[0], "label": row[1]} if row else {"code": "public", "label": "公開"}
    return render_template('aikotoba.html', current=current, **get_sidebar_data(selected_month=request.args.get('month')))


@app.post('/aikotoba/join')
def join_aikotoba():
    code = request.form.get('code', '').strip()
    if not code:
        return redirect(url_for('aikotoba_settings'))
    engine = connect_db()
    username = session.get('auth_user')
    with engine.begin() as conn:
        aid = conn.execute(text("SELECT id FROM aikotoba WHERE code = :c AND active = 1"), {"c": code}).scalar()
        if not aid:
            session['aikotoba_error'] = '合言葉が見つかりません。'
            return redirect(url_for('aikotoba_settings'))
        conn.execute(text("UPDATE users SET aikotoba_id = :aid WHERE username = :u"), {"aid": aid, "u": username})
    return redirect(url_for('aikotoba_settings'))


@app.post('/aikotoba/leave')
def leave_aikotoba():
    engine = connect_db()
    username = session.get('auth_user')
    public_id = get_aikotoba_id("public")
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET aikotoba_id = :aid WHERE username = :u"), {"aid": public_id, "u": username})
    return redirect(url_for('aikotoba_settings'))


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
        public_id = get_aikotoba_id("public")
        engine = connect_db()
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO users (username, password, aikotoba_id) VALUES (:u, :p, :aid)"), {"u": username, "p": "external", "aid": public_id})
    session['auth_user'] = username
    # Redirect back to the original page if available
    next_url = session.pop('post_login_redirect', None)
    if next_url and isinstance(next_url, str) and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(url_for('index'))

@app.route('/edit/<int:transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    engine = connect_db()
    transaction = get_transaction_by_id(transaction_id)

    if not transaction:
        return "Transaction not found", 404

    aid = _get_current_user_aikotoba_id()
    main_categories, all_sub_categories = get_categories(engine, aikotoba_id=aid)

    if request.method == 'POST':
        sub_category_id = request.form['sub_category_id']
        transaction_date = request.form['date']
        transaction_type = request.form['type']
        detail = request.form.get('detail', '')
        raw_amount = request.form['amount']
        try:
            amount = int(''.join(ch for ch in raw_amount if (ch.isdigit() or ch == '-')) or '0')
        except Exception:
            amount = 0

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
                    WHERE id = :id AND aikotoba_id = :aid
                    """
                ),
                {
                    "id": transaction_id,
                    "sub_category_id": sub_category_id,
                    "amount": amount,
                    "type": transaction_type,
                    "date": transaction_date,
                    "detail": detail,
                    "aid": _get_current_user_aikotoba_id(),
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
    aid = _get_current_user_aikotoba_id()
    main_categories, sub_categories = get_categories(engine, aikotoba_id=aid)

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
    for main in main_categories:
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
    import pandas as pd
    aid = _get_current_user_aikotoba_id()
    monthly_summary_df = get_monthly_summary(aikotoba_id=aid)

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

    # Determine a focus month for insights (use end of range or latest available)
    if month_options:
        focus_month = selected_end or month_options[-1]
    else:
        focus_month = datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m')

    # Prepare data for Chart.js
    if not monthly_summary_df.empty:
        labels = monthly_summary_df['month'].dt.strftime('%Y-%m').tolist()
        monthly_values = monthly_summary_df['当月収支'].astype(float).tolist()
        cumulative_values = monthly_summary_df['累計資産'].astype(float).tolist()
    else:
        labels, monthly_values, cumulative_values = [], [], []

    chart_data = json.dumps({
        'labels': labels,
        'monthly': monthly_values,
        'cumulative': cumulative_values,
    })

    # Build insight cards (先月比/前年比、支出ベース)
    engine = connect_db()
    cards = build_insights_cards(engine, focus_month, aid, threshold=10)

    return render_template(
        'graphs.html',
        chart_data=chart_data,
        month_options=month_options,
        selected_start_month=selected_start,
        selected_end_month=selected_end,
        cards=cards,
        focus_month=focus_month,
        **get_sidebar_data(selected_month=request.args.get('month'))
    )

# ===== Sub-category JSON API (for categories UX) =====

@app.get('/api/sub_categories')
def api_get_sub_categories():
    engine = connect_db()
    main_category_id = request.args.get('main_category_id')
    q = request.args.get('q')
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int)

    base_query = """
        SELECT sc.id, sc.name as sub_name, sc.main_category_id,
               mc.name as main_name, sc.icon as icon
          FROM sub_categories sc
          JOIN main_categories mc ON sc.main_category_id = mc.id
         WHERE 1 = 1
    """
    count_query = """
        SELECT COUNT(*)
          FROM sub_categories sc
          JOIN main_categories mc ON sc.main_category_id = mc.id
         WHERE 1 = 1
    """
    params = {}
    # scope by current user's aikotoba
    aid = _get_current_user_aikotoba_id()
    base_query += " AND sc.aikotoba_id = :aid"
    count_query += " AND sc.aikotoba_id = :aid"
    params['aid'] = aid
    if main_category_id:
        base_query += " AND sc.main_category_id = :mid"
        count_query += " AND sc.main_category_id = :mid"
        params['mid'] = main_category_id
    if q:
        base_query += " AND (sc.name LIKE :q OR mc.name LIKE :q)"
        count_query += " AND (sc.name LIKE :q OR mc.name LIKE :q)"
        params['q'] = f"%{q}%"
    base_query += " ORDER BY mc.id ASC, sc.id ASC"

    with engine.connect() as conn:
        total_count = conn.execute(text(count_query), params).scalar()

        if limit is not None:
            base_query += f" LIMIT {limit}"
        if offset is not None:
            base_query += f" OFFSET {offset}"

        rows = conn.execute(text(base_query), params).mappings().all()
        data = [
            {
                'id': r['id'],
                'name': r['sub_name'],
                'main_category_id': r['main_category_id'],
                'main_category_name': r['main_name'],
                'icon': r['icon'],
            }
            for r in rows
        ]
    return jsonify({"items": data, "total_count": total_count})


@app.post('/api/sub_categories')
def api_create_sub_category():
    engine = connect_db()
    payload = request.get_json(force=True, silent=True) or {}
    mid = payload.get('main_category_id')
    name = payload.get('name')
    if not mid or not name:
        return jsonify({"error": "main_category_id と name は必須です"}), 400
    with engine.begin() as conn:
        # Inherit aikotoba from main category
        aid = conn.execute(text("SELECT aikotoba_id FROM main_categories WHERE id = :mid"), {"mid": mid}).scalar()
        res = conn.execute(text(
            "INSERT INTO sub_categories (main_category_id, name, aikotoba_id) VALUES (:mid, :name, :aid)"
        ), {"mid": mid, "name": name, "aid": aid})
        new_id = res.lastrowid
        try:
            pass
        except Exception:
            pass
    return jsonify({"id": new_id}), 201


@app.patch('/api/sub_categories/<int:sub_id>')
def api_update_sub_category(sub_id: int):
    engine = connect_db()
    payload = request.get_json(force=True, silent=True) or {}
    allowed = {'name', 'main_category_id', 'icon'}
    fields = {k: payload[k] for k in allowed if k in payload}
    if not fields:
        return jsonify({"error": "更新対象フィールドがありません"}), 400
    # If main_category_id changes, sync aikotoba_id from the new main category
    set_parts = []
    for k in fields.keys():
        set_parts.append(f"{k} = :{k}")
    if 'main_category_id' in fields:
        set_parts.append("aikotoba_id = (SELECT aikotoba_id FROM main_categories WHERE id = :main_category_id)")
    set_clause = ", ".join(set_parts)
    fields['id'] = sub_id
    with engine.begin() as conn:
        r = conn.execute(text(f"UPDATE sub_categories SET {set_clause} WHERE id = :id"), fields)
        if r.rowcount:
            try:
                pass
            except Exception:
                pass
    return jsonify({"updated": r.rowcount})


@app.delete('/api/sub_categories/<int:sub_id>')
def api_delete_sub_category(sub_id: int):
    engine = connect_db()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM transactions WHERE sub_category_id = :sid"), {"sid": sub_id})
        r = conn.execute(text("DELETE FROM sub_categories WHERE id = :sid"), {"sid": sub_id})
        if r.rowcount:
            try:
                pass
            except Exception:
                pass
    return jsonify({"deleted": r.rowcount})

# ===== Main-category JSON API (for color/icon editing) =====

@app.get('/api/main_categories')
def api_get_main_categories():
    engine = connect_db()
    aid = _get_current_user_aikotoba_id()
    query = "SELECT id, name, icon FROM main_categories WHERE aikotoba_id = :aid ORDER BY id ASC"
    with engine.connect() as conn:
        rows = conn.execute(text(query), {"aid": aid}).mappings().all()
        data = [dict(r) for r in rows]
    return jsonify(data)


@app.patch('/api/main_categories/<int:main_id>')
def api_update_main_category(main_id: int):
    engine = connect_db()
    payload = request.get_json(force=True, silent=True) or {}
    allowed = {'name', 'icon'}
    fields = {k: payload[k] for k in allowed if k in payload}
    if not fields:
        return jsonify({"error": "更新対象フィールドがありません"}), 400
    set_clause = ", ".join([f"{k} = :{k}" for k in fields.keys()])
    fields['id'] = main_id
    fields['aid'] = _get_current_user_aikotoba_id()
    with engine.begin() as conn:
        r = conn.execute(text(f"UPDATE main_categories SET {set_clause} WHERE id = :id AND aikotoba_id = :aid"), fields)
    return jsonify({"updated": r.rowcount})

# ===== Activity: others since my last =====

@app.get('/api/entries/others_since_my_last')
def api_others_since_my_last():
    engine = connect_db()
    aid = _get_current_user_aikotoba_id()
    me = session.get('auth_user') or 'guest'
    limit = request.args.get('limit', default=5, type=int) or 5
    limit = min(max(limit, 1), 20)
    scope = request.args.get('scope', default='month')
    ym = request.args.get('m') or request.args.get('month') or None
    if not ym:
        ym = datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m')

    params = {"aid": aid, "me": me}
    cond = "WHERE aikotoba_id = :aid AND created_by = :me"
    if scope == 'month':
        cond += " AND strftime('%Y-%m', date) = :ym"
        params["ym"] = ym
    with engine.connect() as conn:
        # Fallback if created_by column does not exist
        has_cb = False
        try:
            cols = conn.execute(text("PRAGMA table_info(transactions)")).fetchall()
            has_cb = any(c[1] == 'created_by' for c in cols)
        except Exception:
            has_cb = False

        try:
            last_my_id = conn.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM transactions {cond}"), params).scalar() or 0
        except Exception:
            # no created_by -> treat as 0
            last_my_id = 0

        q = (
            """
            SELECT t.id, t.amount, t.detail, t.date,
                   sc.name AS sub_category, t.created_by AS author
              FROM transactions t
              LEFT JOIN sub_categories sc ON sc.id = t.sub_category_id
             WHERE t.aikotoba_id = :aid
               AND ({created_by_clause})
               AND t.id > :last_id
               AND t.type IN ('収入','支出')
            """
        )
        created_by_clause = "1=1"
        if has_cb:
            created_by_clause = "(t.created_by IS NULL OR t.created_by <> :me)"
        q = q.format(created_by_clause=created_by_clause)
        p = {"aid": aid, "me": me, "last_id": int(last_my_id)}
        if scope == 'month':
            q += " AND strftime('%Y-%m', t.date) = :ym"
            p["ym"] = ym
        q += " ORDER BY t.id DESC LIMIT :lim"
        p["lim"] = limit
        rows = conn.execute(text(q), p).mappings().all()
        items = [dict(r) for r in rows]
        count = len(items)
    return jsonify({
        "since_my_id": int(last_my_id),
        "scope": scope,
        "ym": ym,
        "count": count,
        "items": items,
    })

## SSE removed per rollback request


# ===== Invites (QR招待) =====

## QR invite helpers removed


# Invites feature removed due to performance concerns.

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
