# 5タスク・ロードマップ（Flask単体向けチケット化）

> 目的：既存の良いUXを崩さず、体感品質と継続率を“短工数”で底上げする  
> 対象：Flask + Jinja2 + 素のJS/CSS（必要に応じてCDN）/ SQLite

---

## TASK-001: 月次ヘッダーに「予測着地」と「日割り許容額」を追加（sticky＋スワイプ）

**目的**  
- 月の“現状”だけでなく“この先どうなるか”を即時に可視化し、毎日の支出意思決定を支援する。

**成果物（Deliverables）**  
- stickyヘッダー（左右月移動、進捗バー、予測着地、日割り許容）  
- モバイルの左右スワイプでの月変更  
- 予測計算ユーティリティ（サーバ側）

**具体指示（Implementation）**  
- サーバ（`utils/budget.py`）  
  ```python
  from datetime import date
  import calendar

  def month_context(budget:int, spent:int, today:date):
      days_in_month = calendar.monthrange(today.year, today.month)[1]
      days_passed   = today.day
      days_left     = max(days_in_month - days_passed, 1)
      forecast      = int((spent / max(days_passed,1)) * days_in_month)
      per_day       = int(max(budget - spent, 0) / days_left)
      progress_pct  = int(100 * spent / max(budget,1))
      return dict(forecast=forecast, per_day=per_day, progress_pct=progress_pct,
                  days_in_month=days_in_month, days_left=days_left)
  ```
- ルートで当月の `budget, spent` を集計→`render_template` に渡す（既存集計を流用）。
- テンプレ（`templates/_month_header.html`）  
  ```html
  <header class="month-header">
    <button id="mPrev" aria-label="前の月">‹</button>
    <div id="monthLabel">{{ month_label }}</div>
    <button id="mNext" aria-label="次の月">›</button>

    <div class="budget-row">
      <div class="bar"><span id="barFill" style="width: {{ ctx.progress_pct }}%"></span></div>
      <div class="meta" aria-live="polite">
        残額: ¥{{ (budget - spent)|int|format }} / 予測着地: ¥{{ ctx.forecast|int|format }} / 1日許容: ¥{{ ctx.per_day|int|format }}
      </div>
    </div>
  </header>
  <style>
    .month-header{position:sticky;top:0;background:#fff;z-index:20;box-shadow:0 1px 0 rgba(0,0,0,.06)}
    .bar{height:8px;background:#eee;border-radius:9999px;overflow:hidden}
    #barFill{display:block;height:100%;background:#2563eb;transition:width .5s ease}
    .budget-row{display:grid;gap:.5rem}
  </style>
  ```
- JS（月移動／スワイプ）（`static/js/month-nav.js`）  
  ```js
  function gotoMonth(offset){
    const url=new URL(location.href);
    const ym=(url.searchParams.get('m')||document.body.dataset.currentYm).split('-').map(Number);
    const d=new Date(ym[0], ym[1]-1+offset, 1);
    url.searchParams.set('m', `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`);
    location.href=url.toString();
  }
  document.getElementById('mPrev')?.addEventListener('click',()=>gotoMonth(-1));
  document.getElementById('mNext')?.addEventListener('click',()=>gotoMonth(1));
  let sx=0; window.addEventListener('touchstart',e=>sx=e.touches[0].clientX,{passive:true});
  window.addEventListener('touchend',e=>{
    const dx=e.changedTouches[0].clientX-sx; if(Math.abs(dx)>60) gotoMonth(dx<0?1:-1);
  },{passive:true});
  ```
- テンプレ呼び出し：`{% include "_month_header.html" %}`

**受け入れ基準（AC）**  
- ヘッダーはスクロールしても常時可視。  
- 月変更：ボタン/スワイプの双方で1操作。  
- 進捗バーは金額更新直後に視覚更新（再描画 or Live値反映）。  
- 予測・日割り許容は小数点なし、3桁区切り、日本語表記。

**テスト**  
- 2月/うるう年、月初/中旬/月末の境界、予算0/少額/超過。  
- モバイル（Android/Chrome, iOS/Safari）でスワイプ感度確認。

---

## TASK-002: 一覧の「金額等幅＋カテゴリ色固定＋アイコン」適用

**目的**  
- 一覧を“瞬間で読める”状態にし、金額とカテゴリの結びつきを強化。

**成果物**  
- 金額セル：`tabular-nums`・右寄せ・収入/支出の淡い色分け  
- カテゴリ：色（HEX）とアイコン（emoji/コード）を固定表示

**具体指示**  
- スキーマ変更（SQLite）：  
  ```sql
  ALTER TABLE categories ADD COLUMN color TEXT DEFAULT '#64748b';
  ALTER TABLE categories ADD COLUMN icon  TEXT DEFAULT '💡';
  ```
- 初期データ整備（管理画面/SQLで一括更新OK。例）  
  ```sql
  UPDATE categories SET color='#ef4444', icon='🍔' WHERE name='外食';
  UPDATE categories SET color='#10b981', icon='🚌' WHERE name='交通';
  ```
- テンプレ（`templates/_list_item.html`）  
  ```html
  <li class="row" id="row-{{ item.id }}">
    <span class="cat-pill" style="background: {{ item.category.color }}">{{ item.category.icon }}</span>
    <span class="memo" title="{{ item.memo }}">{{ item.memo }}</span>
    <span class="date">{{ item.date }}</span>
    <span class="amount {{ 'inc' if item.amount>0 else 'exp' }}">{{ '{:,.0f}'.format(item.amount) }}</span>
  </li>
  <style>
    .row{display:grid;grid-template-columns:auto 1fr auto auto;gap:.5rem;align-items:center;padding:.5rem 0;border-bottom:1px solid #eee}
    .memo{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .cat-pill{width:28px;height:28px;border-radius:9999px;display:grid;place-items:center;color:#fff;font-size:12px}
    .amount{font-variant-numeric: tabular-nums; text-align:right}
    .amount.exp{color:#b91c1c} .amount.inc{color:#047857}
  </style>
  ```
- クエリ最適化：一覧APIで`JOIN categories`し、色/アイコンを1クエリで取得。

**受け入れ基準（AC）**  
- 金額桁ズレ無し（縦に並べて等幅が揃う）。  
- すべての画面でカテゴリ色/アイコンが一貫。  
- 長いメモでもレイアウト崩れ無し（省略表示）。

**テスト**  
- 収入/支出/0円の色ルール、英数字・日本語混在のメモ、1000件超でのスクロール性能。

---

## TASK-003: 入力フローの無摩擦化（MRUピル＋Enter遷移＋金額フォーマット）

**目的**  
- 1レコード追加の手数を最小化し、日次記帳率を上げる。

**成果物**  
- 入力順：金額→カテゴリ→日付→メモ（Enter/Nextで遷移）  
- 最近カテゴリ（MRU 3件）ピル表示とワンタップ選択  
- 金額のリアルタイム3桁区切り（送信時は数値化）

**具体指示**  
- テンプレにMRUエリア：  
  ```html
  <div id="mruCats" class="mru"></div>
  <select id="category" name="category_id">…</select>
  <style>.mru{display:flex;gap:.5rem;margin:.5rem 0}.mru .pill{padding:.25rem .5rem;border-radius:9999px;background:#f1f5f9}</style>
  ```
- JS（`static/js/input-flow.js`）  
  ```js
  // Enterで次へ
  const order=['amount','category','date','memo'];
  order.forEach((id,i)=>{
    document.getElementById(id)?.addEventListener('keydown',e=>{
      if(e.key==='Enter'){ e.preventDefault(); document.getElementById(order[i+1])?.focus(); }
    });
  });

  // MRU
  const KEY='mru_categories';
  function mruSet(id,name){
    const mru=(JSON.parse(localStorage.getItem(KEY)||'[]').filter(x=>x.id!==id));
    mru.unshift({id,name}); localStorage.setItem(KEY, JSON.stringify(mru.slice(0,3)));
  }
  function mruRender(){
    const wrap=document.getElementById('mruCats'); if(!wrap) return;
    const mru=JSON.parse(localStorage.getItem(KEY)||'[]');
    wrap.innerHTML=mru.map(c=>`<button type="button" class="pill" onclick="selectCat('${c.id}','${c.name}')">${c.name}</button>`).join('');
  }
  window.selectCat=(id,name)=>{ document.getElementById('category').value=id; mruSet(id,name); };

  // 金額フォーマット
  const nf=new Intl.NumberFormat('ja-JP'); const amt=document.getElementById('amount');
  amt?.addEventListener('input',()=>{
    const v=amt.value.replace(/[^\d\-]/g,''); amt.value = v ? nf.format(Number(v)) : '';
  });

  // submit時に数値へ
  document.querySelector('form#entry')?.addEventListener('submit',()=>{
    if(amt) amt.value = (amt.value||'').replace(/[^\d\-]/g,'');
    const opt=document.querySelector('#category option:checked'); if(opt) mruSet(opt.value, opt.textContent);
  });

  mruRender();
  ```
- サーバ側で金額を `int(request.form['amount'])` で安全にパース。

**受け入れ基準（AC）**  
- マウス無しでもEnterだけで入力完了。  
- 直近3カテゴリが常に上部に表示・選択可能。  
- 送信後に数値が正しく登録（マイナス、0、空入力の検証）。

**テスト**  
- テンキー表示（`inputmode="numeric"`）、Back/ForwardでのMRU保持、Safari/Chromeでの日本語IME入力。

---

## TASK-004: 分析に“自然文カード（先月比/前年比）”を追加

**目的**  
- グラフを見なくても“何が増減したか”を一読で把握し、行動に繋げる。

**成果物**  
- 変化が大きいカテゴリの自然文カード（クリックでカテゴリ詳細にジャンプ）  
- サブスク年間換算カード

**具体指示**  
- サーバ（`services/insights.py`）  
  ```python
  def delta_card(name, cur:int, prev:int, threshold=10):
      if prev==0: return None
      rate = int((cur - prev) / prev * 100)
      if abs(rate) < threshold: return None
      sign = '+' if rate>0 else ''
      amount = cur - prev
      return dict(
        text=f"{name} {sign}{rate}%（{sign}¥{abs(amount):,}）",
        category=name, rate=rate, diff=amount
      )
  ```
- 月別合計（カテゴリ単位）をSQL/ORMで取得し、当月vs先月・当月vs前年同月をループしてカード生成。  
- テンプレ（`templates/_insights.html`）  
  ```html
  <section class="insights">
    {% for c in cards %}
      <a class="card {{ 'up' if c.rate>0 else 'down' }}" href="{{ url_for('list', m=current_ym, cat=c.category) }}">
        {{ c.text }}
      </a>
    {% endfor %}
  </section>
  <style>
    .insights{display:grid;gap:.5rem}
    .card{padding:.75rem 1rem;border:1px solid #e5e7eb;border-radius:.75rem;text-decoration:none;display:block}
    .card.up{background:#fff7ed} .card.down{background:#ecfeff}
  </style>
  ```
- サブスク年間換算：`sum(monthly_fee)*12` を算出しカード表示。

**受け入れ基準（AC）**  
- 増減が±10%以上のカテゴリのみカード化（ノイズ抑制）。  
- クリックで一覧に遷移し、該当カテゴリでフィルタ済み。  
- 日本語表現のぶれ無し、金額は3桁区切り。

**テスト**  
- 前月データが無い場合（カード非表示）、極端な値（0→大きい値）での表現、負の支出（返金）。

---

<!-- ## TASK-005: 合言葉の“QR招待＋権限＋更新通知（SSE）”を追加

**目的**  
- 共同家計の導入摩擦を最小化し、リアルタイム性で放置を防ぐ。

**成果物**  
- 招待作成API（TTL付きトークン、閲覧/編集ロール）  
- 招待QRエンドポイント、参加フロー  
- 更新通知（Server-Sent Eventsで軽量実装）

**具体指示**  
- スキーマ（SQLite）  
  ```sql
  CREATE TABLE IF NOT EXISTS invites(
    id INTEGER PRIMARY KEY,
    household_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('viewer','editor')),
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
  );
  -- householdとuserの中間テーブルにrole列が無ければ追加
  ALTER TABLE household_users ADD COLUMN role TEXT DEFAULT 'editor';
  ```
- ルート  
  ```python
  # 1) 招待作成
  @app.post("/invite")
  @login_required
  def invite_create():
      import secrets, datetime as dt
      token = secrets.token_urlsafe(16)
      expires = (dt.datetime.utcnow() + dt.timedelta(hours=24)).isoformat()
      db.execute("INSERT INTO invites(household_id, token, role, expires_at, created_at) VALUES(?,?,?,?,datetime('now'))",
                 (current_user.household_id, token, request.form.get('role','viewer'), expires))
      return {"token": token, "qr": url_for('invite_qr', token=token, _external=True)}

  # 2) QR画像
  @app.get("/invite/qr/<token>")
  def invite_qr(token):
      import qrcode, io
      url = url_for('invite_join', token=token, _external=True)
      buf=io.BytesIO(); qrcode.make(url).save(buf, 'PNG'); buf.seek(0)
      return send_file(buf, mimetype="image/png")

  # 3) 参加
  @app.get("/join")
  @login_required
  def invite_join():
      token=request.args.get('token')
      row=db.fetchone("SELECT household_id, role, expires_at FROM invites WHERE token=?", (token,))
      assert row, "招待が見つかりません"
      # expires検証→ household_usersへ追加 → 招待無効化/削除
      return redirect(url_for('household_settings'))
  ```
- SSE（最小構成）  
  ```python
  @app.get('/events')
  @login_required
  def sse():
      from flask import Response
      def stream():
          last_id=0
          while True:
              ev=db.fetchone("SELECT id, message FROM events WHERE user_id=? AND delivered=0 ORDER BY id DESC LIMIT 1", (current_user.id,))
              if ev and ev['id']!=last_id:
                  yield f"data: {ev['message']}\n\n"; last_id=ev['id']
              time.sleep(2)
      return Response(stream(), mimetype='text/event-stream')
  ```
- クライアント  
  ```js
  const es = new EventSource('/events');
  es.onmessage = e => showToast(JSON.parse(e.data)); // {message:"◯◯さんが支出を追加: ¥1,200"}
  ```

**受け入れ基準（AC）**  
- 招待作成→QR表示→他端末で読み取り→参加完了までノンストップ。  
- 役割（viewer/editor）に応じ、編集UIが自動で抑制。  
- 支出追加/削除/編集時に相手端末へ10秒以内に通知。

**テスト**  
- 招待TTL切れ、同一トークンの再利用、権限違反操作のブロック。  
- オフライン/再接続時のSSE復帰。  
- QRの誤読（無効トークン）の例外表示。 -->

## TASK-006: 「自分の前回追加以降」に他ユーザーが追加した明細を表示

**目的**
- 自分が最後に記帳してからの“他人の追加”を一目で把握し、家計の同期コストを下げる。
- 通知を重くしない（差分ポーリング、最近5件限定）。


### 1) スキーマ & インデックス
**やること**
- 既存 `entries` テーブルを対象（前提: 自動採番 `id`, `household_id`, `user_id`, `created_at`）。
- 高速化のための複合インデックスを追加。

**SQL**
```sql
CREATE INDEX IF NOT EXISTS idx_entries_household_user_id
ON entries(household_id, user_id, id DESC);

CREATE INDEX IF NOT EXISTS idx_entries_household_id
ON entries(household_id, id DESC);
```

> `id` が全体で単調増加なら「以降」は `id > last_my_id` でOK。  
> `created_at` を使う場合は `... AND created_at > ?` でも可（ただし索引設計が増える）。


### 2) サーバAPI：`GET /api/entries/others_since_my_last?limit=5&scope=month|all`
**仕様**
- カレント世帯（`current_user.household_id`）内で、
  - **自分の最新登録ID**（`last_my_id`）を計算
  - **他ユーザーの `id > last_my_id`** の明細を取得（降順、最大 `limit` 件）
- `scope=month` のときは**当月内**に限定（既定: `month` 推奨）。

**Flask（擬似コード）**
```python
from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import date

@app.get("/api/entries/others_since_my_last")
@login_required
def others_since_my_last():
    limit = min(request.args.get("limit", type=int, default=5), 20)
    scope = request.args.get("scope", default="month")
    hh = current_user.household_id
    me = current_user.id

    # 1) 自分の最新ID（必要なら当月に限定）
    params = [hh, me]
    cond = "WHERE household_id=? AND user_id=?"
    if scope == "month":
        ym = request.args.get("m")  # 'YYYY-MM'
        if not ym:
            today = date.today()
            ym = f"{today.year}-{today.month:02d}"
        cond += " AND strftime('%Y-%m', created_at)=?"
        params.append(ym)
    last_my_id = (db.fetchone(f"SELECT COALESCE(MAX(id),0) AS id FROM entries {cond}", tuple(params))["id"])

    # 2) 他ユーザーの last_my_id 以降
    q = """
      SELECT e.id, e.amount, e.memo, e.created_at,
             c.name AS category, u.display_name AS author
      FROM entries e
      JOIN users u ON u.id = e.user_id
      LEFT JOIN categories c ON c.id = e.category_id
      WHERE e.household_id = ?
        AND e.user_id <> ?
        AND e.id > ?
    """
    p = [hh, me, last_my_id]
    if scope == "month":
        q += " AND strftime('%Y-%m', e.created_at)=?"
        p.append(ym)
    q += " ORDER BY e.id DESC LIMIT ?"
    p.append(limit)

    items = db.fetchall(q, tuple(p))

    # カウントだけ欲しい場面用
    count_q = "SELECT COUNT(1) AS cnt FROM (" + q.replace("SELECT e.id, e.amount, e.memo, e.created_at, c.name AS category, u.display_name AS author", "SELECT 1") + ")"
    cnt = db.fetchone(count_q, tuple(p))["cnt"]

    return jsonify({
      "since_my_id": last_my_id,
      "scope": scope,
      "count": cnt,
      "items": items
    })
```

**エッジケース**
- 自分の登録が一度も無い → `last_my_id = 0` として他人の最近5件を返す。
- 当月に自分の登録が無い（`scope=month`）→ メッセージ「当月は未登録です（前回: YYYY-MM-DD）」をUIで補足。


### 3) フロントUI（ドロップダウン＋バナー）
**やること**
- 通知ベル内に「**自分の前回追加以降**」タブを追加（既存 NOTIFY-LITE と並置）。
- 一覧画面の先頭に**薄いバナー**：「前回登録以降に他の人が *N* 件追加 → 詳細」。
- 非可視時は停止、可視時のみ**45秒おき**に更新（NOTIFY-LITEと同じリズム）。

**HTML（例）**
```html
<div class="since-banner" id="sinceBanner" hidden>
  前回のあなたの登録以降に <b id="sinceCount">0</b> 件追加されています。
  <button id="sinceOpen">詳細</button>
</div>

<div id="sinceMenu" class="menu" hidden></div>
```

**CSS（例）**
```css
.since-banner{margin:.5rem 0;padding:.5rem .75rem;background:#f1f5f9;border:1px solid #e5e7eb;border-radius:.5rem}
#sinceMenu .item{display:grid;grid-template-columns:1fr auto;gap:.25rem;padding:.5rem;border-radius:.5rem}
#sinceMenu .item:hover{background:#f8fafc}
#sinceMenu time{color:#64748b;font-size:12px}
```

**JS（差分ポーリング）**
```js
async function fetchOthersSinceMyLast(scope='month', limit=5){
  const url = `/api/entries/others_since_my_last?scope=${scope}&limit=${limit}${window.currentYm ? '&m='+window.currentYm : ''}`;
  const res = await fetch(url, {cache:'no-store'});
  if(!res.ok) return;
  const data = await res.json();
  renderSince(data);
}

function renderSince(data){
  const banner = document.getElementById('sinceBanner');
  const countEl = document.getElementById('sinceCount');
  const menu = document.getElementById('sinceMenu');

  countEl.textContent = data.count;
  banner.hidden = data.count === 0;

  menu.innerHTML = data.items.map(it=>`
    <div class="item">
      <div>
        <b>${escapeHtml(it.author)}</b> が <b>${escapeHtml(it.category||'未分類')}</b> を登録：¥${Number(it.amount).toLocaleString('ja-JP')}
        <div class="memo">${escapeHtml(it.memo||'')}</div>
      </div>
      <time>${timeAgo(it.created_at)}</time>
    </div>
  `).join('') || '<div class="item">新しい追加はありません</div>';
}

document.getElementById('sinceOpen').addEventListener('click', ()=>{
  const m = document.getElementById('sinceMenu');
  m.hidden = !m.hidden;
});

let sinceTimer;
function scheduleSince(ms=45000){
  clearInterval(sinceTimer);
  sinceTimer = setInterval(()=>{ if(!document.hidden) fetchOthersSinceMyLast(); }, ms);
}
document.addEventListener('visibilitychange', ()=>{ if(!document.hidden) fetchOthersSinceMyLast(); });

fetchOthersSinceMyLast();
scheduleSince();
```


### 4) 受け入れ基準（AC）
- 一覧上部のバナーに **件数** が出る（0件なら非表示）。
- メニューで **最大5件** が時系列降順で表示され、**著者名・カテゴリ・金額・メモ・相対時刻** が見える。
- 当月スコープで月切替すると、APIも切り替わる（`m=YYYY-MM`）。
- パフォーマンス：可視時45秒/1リクエスト、**非可視時0**。レスポンスは ~数ms〜十数msで返る（索引使用）。


### 5) テスト
- 自分が**直前に登録**→ 別ユーザーが登録 → 45秒以内に件数が増える。
- 自分登録が**当月にない**→ バナーに補足文 or 非表示（仕様選択）。
- 大量データ（10万行）でもAPIの実行計画に `idx_entries_household_user_id` が使われることを確認。
- 時刻/IDの境界：**同一秒**に複数登録されても `id` 基準で正しく計上。


### 6) オプション（将来）
- **“既読化”**の概念を足す：メニューを開いたら `last_ack_others_id = max(id)` をユーザー設定に保存し、「未読」バッジをより厳密に。
- **スレッド表示**：同一ユーザーの連続登録を1アイテムに折りたたみ（`+N件`）。


#### 補足（なぜ“自分の最後のID”基準？）
- サーバ側で毎回 **`MAX(id)` を1回** 取るだけで閾値が決まる → 計算が軽い  
- “自分が最後に触った時刻”を勝手に保存しなくてよい（UXが明快）  
- 競合や遅延があっても **順序はIDが保証**（AUTOINCREMENT）  

---

## TASK-007: モーション＆マイクロインタラクションの品位向上（Flask単体）

**目的**
- 認知負荷を下げ、操作の因果を“自然に理解”できる微小アニメーションを付与して**知覚品質**を底上げする。
- 体感速度を落とさず（むしろ上げて）、**A11y（prefers-reduced-motion）**に完全準拠。

**範囲**
- Flask + Jinja2 + 素のCSS/JS（必要ならCDN）。SPA化不要。


### 成果物（Deliverables）
1. **モーション設計トークン**（CSSカスタムプロパティ：時間/距離/イージング）
2. **コンポーネント別モーション**  
   - モーダル/ドロワーの `fade + slide-up (200ms)`  
   - 追加直後の**行ハイライト（pulse 1s）**  
   - 進捗バー（widthトランジション 0.5s）  
   - トースト通知（enter/exit 200ms + 自動閉）  
   - スケルトン（500ms以上で自動表示、shimmer）  
   - ボタン押下の**微スケール**（押下感フィードバック）
3. **JSユーティリティ**（class付替え/トーストAPI/Reduced Motion尊重）
4. **A11y適合**（`prefers-reduced-motion: reduce` 時はアニメ最小化、focus可視、aria適用）


### 実装（CSS：`static/css/motion.css`）
```css
/* === Motion Tokens === */
:root{
  --dur-quick: 150ms;
  --dur-base:  200ms;
  --dur-slow:  300ms;
  --e-out:     cubic-bezier(.2,.8,.2,1);
  --e-in:      cubic-bezier(.4,0,1,1);
  --e-inout:   cubic-bezier(.4,0,.2,1);
  --e-bounce:  cubic-bezier(.34,1.56,.64,1);
  --e-smooth:  cubic-bezier(.22,.61,.36,1);
  --e-emph:    cubic-bezier(.12,.8,.22,1);
}

/* Reduced Motion: minimize but keep state clarity */
@media (prefers-reduced-motion: reduce){
  *, *::before, *::after{
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}

/* === Modal/Drawer === */
.modal-backdrop{
  position: fixed; inset: 0; background: rgba(15,23,42,.45);
  opacity: 0; transition: opacity var(--dur-base) var(--e-out);
}
.modal-panel{
  transform: translateY(16px) scale(.98); opacity: 0;
  transition: transform var(--dur-base) var(--e-out),
              opacity var(--dur-base) var(--e-out);
  will-change: transform, opacity;
}
.modal-open .modal-backdrop{ opacity: 1; }
.modal-open .modal-panel{ transform: translateY(0) scale(1); opacity: 1; }

/* === List add pulse === */
.pulse{ animation: pulse-bg 1000ms var(--e-smooth); }
@keyframes pulse-bg{
  0%{ background: #fffbe6; }
  100%{ background: transparent; }
}

/* === Progress bar smooth === */
.progress{ height:8px; background:#e5e7eb; border-radius:9999px; overflow:hidden; }
.progress > span{
  display:block; height:100%; width:0;
  background:#2563eb; transition: width .5s var(--e-out);
}

/* === Toast === */
.toast-host{ position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%);
  display:grid; gap:.5rem; z-index: 70; }
.toast{
  min-width: 240px; max-width: 520px; padding:.75rem 1rem;
  background:#111827; color:#fff; border-radius:.75rem;
  box-shadow:0 8px 24px rgba(0,0,0,.22);
  transform: translateY(8px); opacity: 0;
  transition: transform var(--dur-base) var(--e-out),
              opacity var(--dur-base) var(--e-out);
}
.toast.show{ transform: translateY(0); opacity: 1; }
.toast .actions{ display:flex; gap:.5rem; margin-top:.25rem; }
.toast button{ color:#93c5fd; border:0; background:none; padding:.25rem .5rem; border-radius:.5rem; }
.toast button:hover{ background: rgba(255,255,255,.08); }

/* === Skeleton === */
.skel{ position:relative; overflow:hidden; background:#f1f5f9; border-radius:.5rem; }
.skel::after{
  content:""; position:absolute; inset:0;
  transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.6), transparent);
  animation: shimmer 1200ms infinite;
}
@keyframes shimmer{ 100%{ transform: translateX(100%); } }

/* === Button press micro-scale === */
.btn{ transition: transform var(--dur-quick) var(--e-out), box-shadow var(--dur-quick) var(--e-out); }
.btn:active{ transform: scale(.98); }
.btn:focus-visible{ outline: 3px solid #93c5fd; outline-offset: 2px; }
```


### 実装（JS：`static/js/motion.js`）
```js
// Modal open/close helpers (aria + focus trap minimal)
export function openModal(id){
  const root = document.getElementById(id);
  if(!root) return;
  root.classList.add('modal-open');
  root.removeAttribute('hidden');
  const panel = root.querySelector('.modal-panel');
  const prev = document.activeElement;
  root.dataset.prevFocus = prev && prev.id ? prev.id : '';
  const first = panel.querySelector('[tabindex],button,input,select,textarea,a[href]');
  (first||panel).focus();
  document.body.style.overflow = 'hidden';
}
export function closeModal(id){
  const root = document.getElementById(id);
  if(!root) return;
  root.classList.remove('modal-open');
  // wait for transition end (~200ms) then hide
  setTimeout(()=>{
    root.setAttribute('hidden','');
    document.body.style.overflow = '';
    const prevId = root.dataset.prevFocus;
    if(prevId){ document.getElementById(prevId)?.focus(); }
  }, 200);
}
document.addEventListener('keydown', e=>{
  if(e.key === 'Escape'){
    document.querySelectorAll('.modal-root:not([hidden])')
      .forEach(el => closeModal(el.id));
  }
});

// Toast API
const hostId = 'toastHost';
function ensureHost(){
  let h = document.getElementById(hostId);
  if(!h){
    h = document.createElement('div'); h.id = hostId; h.className = 'toast-host';
    document.body.appendChild(h);
  }
  return h;
}
export function showToast(text, actions=[/* {label, onClick} */], timeout=2500){
  const h = ensureHost();
  const t = document.createElement('div'); t.className = 'toast';
  t.innerHTML = `<div class="body">${escapeHtml(text)}</div>`;
  if(actions.length){
    const ac = document.createElement('div'); ac.className = 'actions';
    actions.forEach(a=>{
      const b = document.createElement('button');
      b.textContent = a.label;
      b.addEventListener('click', ()=>{ a.onClick?.(); dismiss(); });
      ac.appendChild(b);
    });
    t.appendChild(ac);
  }
  h.appendChild(t);
  requestAnimationFrame(()=> t.classList.add('show'));
  const kill = setTimeout(()=> dismiss(), timeout);
  function dismiss(){
    clearTimeout(kill);
    t.classList.remove('show');
    setTimeout(()=> t.remove(), 200);
  }
  return dismiss;
}
function escapeHtml(s){ return (s||'').replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[m])); }

// List add pulse: call after DOM insert
export function pulseRow(rowId){
  const el = document.getElementById(rowId);
  if(!el) return;
  el.classList.add('pulse');
  setTimeout(()=> el.classList.remove('pulse'), 1000);
}

// Progress bar helper
export function setProgress(id, pct){
  const el = document.querySelector(`#${id} > span`);
  if(el) el.style.width = `${Math.max(0, Math.min(100, pct))}%`;
}

// Skeleton control
export function withSkeleton(el, fn){
  // show skeleton if operation > 500ms
  const skel = document.createElement('div'); skel.className='skel'; skel.style.height='1.75rem';
  const t = setTimeout(()=> el.replaceChildren(skel), 500);
  return fn().finally(()=>{ clearTimeout(t); });
}
```

> 依存なし（素のJS）。`type="module"` で読み込めば `export` 利用可。


### テンプレ適用例（Jinja）
```html
<!-- base.html -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/motion.css') }}">
<script type="module" src="{{ url_for('static', filename='js/motion.js') }}"></script>

<!-- Modal -->
<div id="entryModal" class="modal-root" hidden aria-hidden="true">
  <div class="modal-backdrop" onclick="closeModal('entryModal')"></div>
  <div class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="entryTitle">
    <h2 id="entryTitle">支出を登録</h2>
    <!-- form fields -->
    <div class="actions">
      <button class="btn" onclick="closeModal('entryModal')">キャンセル</button>
      <button class="btn btn-primary" onclick="submitEntry()">登録する</button>
    </div>
  </div>
</div>

<!-- Progress -->
<div id="budgetProgress" class="progress"><span style="width: {{ progress_pct }}%"></span></div>
```


### 画面フローへの組み込み（例）
- **登録成功時**：
  ```js
  import { showToast, pulseRow } from '/static/js/motion.js';
  async function submitEntry(){
    const resp = await fetch('/api/entries', {method:'POST', body: new FormData(entryForm)});
    if(resp.ok){
      const { id } = await resp.json();
      prependRowToList(id);           // DOM反映（あなたの既存処理）
      pulseRow(`row-${id}`);          // 追加行を1秒ハイライト
      showToast('登録しました', [
        {label:'元に戻す', onClick: ()=> undoEntry(id) },
        {label:'続けて追加', onClick: ()=> openModal('entryModal') }
      ]);
    }else{
      showToast('保存に失敗しました。通信環境をご確認ください。', [], 4000);
    }
  }
  ```
- **月ヘッダーの進捗更新**：
  ```js
  import { setProgress } from '/static/js/motion.js';
  setProgress('budgetProgress', newPct);
  ```
- **読み込みが重い一覧**：
  ```js
  import { withSkeleton } from '/static/js/motion.js';
  const listHost = document.getElementById('listHost');
  withSkeleton(listHost, async ()=>{
    const html = await fetch('/list/partial').then(r=>r.text());
    listHost.innerHTML = html;
  });
  ```


### A11y & 品質チェック
- [ ] `prefers-reduced-motion` でアニメ短縮（CSSあり）
- [ ] モーダルは `aria-modal="true"` とフォーカス戻し
- [ ] トーストは**重要操作**をボタンで提供（Undo 2.5s）
- [ ] 進捗・残額など**ライブ値**は `aria-live="polite"` を付与
- [ ] すべてのトランジションは **150–250ms** に収める（長過ぎ禁止）


### 受け入れ基準（AC）
- モーダルの**開閉が200ms**で自然（白飛び/カクつき無し）
- 追加行ハイライトが**1秒以内**に消える
- 進捗バーは更新時に**0.4–0.6s**でスムーズに追従
- トーストが**自動で2.5s**後に消える（操作時は即消える）
- `prefers-reduced-motion` で**一括抑制**される


### テスト（最小）
- Android Chrome / iOS Safari / デスクトップ Chrome & Safari で
  - モーダル開→入力→閉で**フォーカスが戻る**
  - 低端末（CPUスロットリング x4）で**フレーム落ちが無い**
  - Reduce Motion 有効時に**トランジションが瞬間化**される
- Lighthouse → **Best Practices/A11y ≥ 95**、**TBT**増加なし


### パフォーマンス配慮
- `will-change` は短時間のみ適用（既にmodal-panelで限定）
- `transform/opacity` 以外のプロパティをアニメしない（レイアウトスラッシング回避）
- JSの setTimeout は**200ms/1000msだけ**。ループ/長時間タイマーは無し


### ロールアウト手順
1. `static/css/motion.css` と `static/js/motion.js` を追加、`base.html` に読み込み
2. モーダル/トーストのマークアップ差し替え（既存クラスに追加適用でも可）
3. 「登録成功」「削除成功」などの箇所で `showToast/pulseRow/setProgress` を呼び出し
4. QA → 本番

> 以上で、見た目の“上質感”と**状態の可視化**が上がり、**既存の良さ**（簡潔さ/軽さ）を維持したまま世界レベルに寄せられます。

---

## 横断チェック（全タスク共通）

- [ ] 文言は丁寧体で統一、3桁区切り・単位は日本語表記  
- [ ] 44×44pxのタップ領域、`aria-live="polite"` の重要数値  
- [ ] モーションは `150–250ms`、`prefers-reduced-motion` 対応  
- [ ] バンドル増は最小限（外部ライブラリはCDN/遅延ロード）  
- [ ] 破壊操作にはUndo（トースト 2.5s）

## 推定工数（目安）
- TASK-001: 0.5〜1.0日  
- TASK-002: 0.5日（初期カテゴリ配色が決まっていれば）  
- TASK-003: 0.5日  
- TASK-004: 1.0日（集計の整備状況に依存）  
- TASK-005: 1.5〜2.0日（権限/通知の網羅テスト含む）

> 先に 001→003→002 を入れると“体感の伸び”が大。004/005は価値が高いがテスト項目が増えるため次スプリント推奨。
