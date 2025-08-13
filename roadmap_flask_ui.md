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

## TASK-005: 合言葉の“QR招待＋権限＋更新通知（SSE）”を追加

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
- QRの誤読（無効トークン）の例外表示。

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
