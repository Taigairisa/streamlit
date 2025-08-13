# AGENTS ガイド（kakeibo_st）

このドキュメントは、エージェント（人/LLM）が毎回リポジトリ全体を読み込まずに素早く安全に作業できるようにするための運用ガイドです。README の要点、実行・開発手順、設計方針、SOP、禁止事項、カスタム指示をここに集約します。

## プロジェクト概要
- 目的: 家計簿（支出/収入/予算）を記録し、進捗・推移を可視化する。
- 技術: Python 3.12 / Flask / Jinja2 / SQLite（Streamlit 由来のコードも一部残置）。
- データ: SQLite DB を `/data/kakeibo.db` に永続化。初回は `data/kakeibo.db` をコピー（Docker）または空スキーマ生成。
- デプロイ: Docker でコンテナ化、Fly.io で運用（ボリューム `/data`）。
- 主要画面: 追加、編集、カテゴリー追加・編集、グラフ、開発者オプション。

## すぐに使う（最短手順）
- ローカル（簡易）
  - 依存を入れる: `uv sync`（推奨。pip を使う場合は `pip install -r requirements.txt`）
  - 注意: 既定の保存先は `/data`。書込できない環境では自動で `./runtime-data` にフォールバック。明示したい場合は `KAKEIBO_DATA_DIR=./runtime-data` を指定。
  - 起動: `uv run streamlit run app.py` → `http://localhost:8501`
- Docker（推奨）
  - ビルド: `docker build -t kakeibo-st .`
  - 実行: `docker run --rm -p 8501:8501 -v $(pwd)/runtime-data:/data kakeibo-st`
  - データは `./runtime-data/kakeibo.db` に永続化。
- Fly.io
  - `fly deploy`（初回は `fly volumes create data --size 1` が必要な場合あり）


## リポジトリマップ（最重要だけ）
- `flask_app.py`: Flask エントリーポイント（ルーティング/テンプレート描画）。
- `kakeibo/db.py`: DB 接続・クエリ・更新・月次集計のユーティリティ。
- `templates/`: Jinja2 テンプレート（`base.html`, `index.html`, `add.html`, `edit_list.html`, `graphs.html`, `dev_options.html`）。
- `templates/partials/`: Jinja2 パーシャル（`sidebar.html` などの共通断片）。
- `static/`: カスタム CSS（Bootstrap/Google Fonts/CDN を併用）。
  - `static/css/style.css`: 全体スタイルとコンポーネント。
  - `static/js/main.js`: グローバル挙動（サイドバー開閉、月セレクト）。
  - `static/js/graphs.js`: グラフページ専用の描画・UI制御。
- `data/kakeibo.db`: 初期 DB（シード）。
- `start-flask.sh` / `Dockerfile.flask`: Flask 起動用。
- `fly.toml`: Fly.io 設定（`/data` マウント含む）。
- `.streamlit/secrets.toml`: Secrets（注意: 機密は本来コミットしない）。
- `requirements.txt` / `pyproject.toml`: 依存一覧。

## DB スキーマ（要点）
- `main_categories(id, name)`
- `sub_categories(id, main_category_id, name)`
- `transactions(id, sub_category_id, amount, type in ['支出','収入','予算'], date 'YYYY-MM-DD', detail)`
- `backup_time(id, time)`
- `users(id, username UNIQUE, password 'scheme:value', role, created_at)`

主な関数（`kakeibo/db.py`）
- `connect_db()` / `exists_db_file()`
- `load_data(conn, sub_category_id)`
- `get_budget_and_spent_of_month(conn, month)`
- `get_categories(conn)`
- `update_data(df, changes)`
- `get_monthly_summary()`

注意
- `load_data` は文字列整形で SQL を生成（SQL インジェクション懸念）。改修時はプレースホルダを使う。

## 画面/機能の要点（Flask 現状）
- 予算進捗: 全ページ上部のカードに表示。月の選択も同カードで変更可能（折りたたみ可）。URL の `month` を全ページで維持。
- サイドバー: オフキャンバス化（開/閉ボタンあり）。メニューはドロップダウンに集約。リンククリックで自動クローズ。
- 贈与見える化: 「贈与」小カテゴリの収入/支出の対比。
- 未入力の月額: 定期カテゴリの未入力リマインド。
- グラフ: 月次収支/累計資産（開始/終了月フィルタ対応）。
- 編集: スプレッドシート風 UI（Tabulator）。セル編集/行追加/削除、ソート、ライブ検索。変更時は「旧→新」の確認ダイアログ。CDN不可時は簡易表へフォールバック。
- 開発者オプション: DB ダウンロード（`/download_db`）、任意 SQL 実行（例外表示）。
- 認証: 未ログイン時は `/login` にリダイレクト。ログインボタンから LINE OAuth へ遷移（`/login/line` → `/callback/line`）。復帰後に元の画面へ戻る。`/logout` でセッションクリア。
 - データスコープ（合言葉）: 合言葉（aikotoba）によりデータを分離。ユーザーは自身の合言葉に紐づくデータのみ閲覧・編集可能。
   - テーブル: `aikotoba(id, code UNIQUE, label, active, created_at)`、各エンティティに `aikotoba_id`（`users`, `main_categories`, `sub_categories`, `transactions`）。
   - 既定の合言葉: `code='public'` を自動生成し、既存データは public に割当。
   - 画面: `/aikotoba` で合言葉参加（コード入力）/解除（publicへ）。新規作成は当面不可。
   - 追加・編集時: 取引は小カテゴリの合言葉を継承。小カテゴリは大カテゴリの合言葉を継承。

## 開発方針（Design Decisions）
- 単一ファイル `flask_app.py` + テンプレートで薄く構成。
- DB は SQLite を単純利用。外部同期（Google Sheets）は将来機能として温存。
- 永続化パスは `/data` を正とし、Docker/Fly で扱いやすくする。
- 変更は局所的・最小限に行い、既存の UI/UX を壊さない。

## コーディング規約（軽量）
- スタイル: 既存に合わせる（関数ベース、グローバル定数利用）。
- 命名: 意味の分かる日本語/英語を混在可。略語は避ける。
- DB アクセス: `connect_db()` を用い、クエリ後は必ず `conn.close()`。
- 例外処理: ユーザーには `st.error`/`st.warning` で分かりやすく通知。
- 依存: 既存の依存に追加する前に用途を README/本書に記載。

- Secrets: `.streamlit/secrets.toml` は旧来の名残。Flask は環境変数（例: `FLASK_SECRET_KEY`）。
- 現在リポにシークレット相当ファイルが含まれるため、実運用ではキーのローテーションと外部秘匿を強く推奨。
- SQL: SQLAlchemy（Core）でパラメータ化済み（`text()` + バインド変数）。
- データ消失対策: バックアップ機能（Google Sheets）は無効。必要なら再有効化し、検証のうえ段階導入。
 - 認証: LINE OAuth の最小実装あり（`LINE_CLIENT_ID`/`LINE_CLIENT_SECRET`/`LINE_REDIRECT_URI`）。機能ガードは未適用（ToDo）。

## テスト/検証（現状）
- スモークチェック（読み取り中心・破壊なし）
  - `uv run scripts/smoke_check.py`
- pytest（任意）
  - `uv run --with pytest -m pytest -q`（pytest が無くても一時依存で実行可）
  - 変更系のテストは現状なし（本番 DB を汚さないため）。必要に応じてテスト用 DB 切替を導入してから追加。

## よくある作業の SOP（手順書）
- 小カテゴリを増やす
  - UI から「カテゴリー追加・編集」→小カテゴリ追加。
  - 既存コード変更は不要。
- ページを 1 つ増やしたい
  - `app.py` のサイドバー `selectbox(options=[...])` に項目追加。
  - 分岐（`if view_category == "...":`）を追加し処理を実装。
- 週次/月次の新しいグラフを追加
  - 集計関数を `app.py` に追加し、`pandas`/`altair`/`st.line_chart` 等で表示。
  - 期間選択 UI は `select_slider` を流用可。
- DB 項目を1つ増やす
  - 破壊的変更。マイグレーション（`ALTER TABLE`）と既存 UI 影響を精査。
  - 必須でなければ `detail` の拡張や補助テーブルで代替を検討。
- Google Sheets 同期を復活
  - コメントアウト箇所（`initialize_db_from_spreadsheet`/`backup_data_to_spreadsheet`）を段階的に再有効化。
  - `secrets.toml` or 環境変数で認証情報を注入し、少量データで検証。

## してはいけないこと（Do/Don't）
- 不要にスキーマを変える／既存 UI を壊す。
- 機密情報のコミット、ログ出力、画面表示。
- 大規模リファクタでファイル/関数名を安易に変更。
- 重い依存の追加（理由と README/本書更新がない場合）。
- SQL を文字列連結で書く（必ず `sqlalchemy.text()` とパラメータを使う）。

## トラブルシュートの要点
- `/data` に書けない: Docker で実行、または `/data` を作成して権限付与。開発時は `KAKEIBO_DATA_DIR=./runtime-data` を指定して回避可。
- グラフが空: 2023-10 以降データのみ対象。期間フィルタを確認。
- 予算進捗が出ない: 「日常」カテゴリの予算/支出が必要。サンプル入力で確認。
- 定期の未入力が出ない: 直近入力日から 1 か月超のデータが必要。

## エージェント向けカスタム指示（LLM/人共通）
- 作業スタイル
  - 変更は最小限・局所的。周辺影響を必ず自己点検。
  - 実装前に「何をどこに書くか」を 1〜2 行で明示。
  - 動かして確認（Docker 推奨）。
  - 考えている言葉も基本は日本語で統一。
  - ユーザー向けの UI 文言は簡潔な日本語で統一。
- 変更時のチェックリスト
  - [ ] README/AGENTS に追記が必要か判断し、必要なら更新。
  - [ ] `/data` 前提で動くか（権限/初期化）を確認。
  - [ ] DB 接続のクローズ漏れなし。
  - [ ] SQL 文字列結合を避ける（可能な範囲で修正）。
  - [ ] 例外時のユーザー通知（`st.error`/`st.warning`）。
  - [ ] 依存を増やした場合は理由・使い方を README/本書に記載。
  - [ ] 認証の挙動（有効/無効時）を確認。ログイン/ログアウトの UX を確認。
- コミット/ブランチ（参考）
  - ブランチ: `feat/...`, `fix/...`, `chore/...`, `docs/...`
  - メッセージ: 和文で要点 + 英単語を混ぜない（任意）。
  - PR: 変更概要、動作確認、スクショ（可能なら）
- 生成 AI 活用の指針
  - 大枠方針→小さな差分の順で提案。
  - 既存コードの語彙/スタイルを尊重。
  - 機密・外部キーはダミー化して提示。

## 環境・設定メモ
- ポート: 5000（Flask） / 8501（旧 Streamlit）
- タイムゾーン: Asia/Tokyo
- 主要パッケージ: `pandas`, `altair`, `streamlit`, `sqlite3`, ほか
- 無効化中の機能: Google Sheets 同期、Gemini 分析
- データディレクトリ: 既定は `/data`。環境変数 `KAKEIBO_DATA_DIR` で上書き可。`/data` に書込不可の場合は自動でリポジトリ内 `./runtime-data` にフォールバック（CI/サンドボックス向け）。

## 将来の改善候補（Flask/UX ToDo）
- 認証ガード: `/edit` `/dev` `/api/*` にログイン必須（Blueprint + before_request）。
- CSRF: 変更系 API にトークン導入（ヘッダ or Flask-WTF）。
- Tabulator のローカル配信（static/vendor）とアセットバンドル。
- 編集UX: 複数行一括編集/バルク保存、ショートカット、列固定、CSV/TSV入出力。
- `/api/transactions` サーバーサイドページング/ソート、簡易キャッシュ。
- 監査ログ: 誰が何をいつ変更したかの記録。
- 404/500 テンプレートと構造化ロギング。

---
### Flask 実装の起動（ローカル）
- 依存インストール: `uv sync` または `pip install -r requirements.txt`
- 起動: `uv run python flask_app.py`（`http://localhost:5000`）
- Docker: `docker build -f Dockerfile.flask -t kakeibo-flask .` → `docker run --rm -p 5000:5000 -v $(pwd)/runtime-data:/data kakeibo-flask`

### API（編集用・JSON）
- GET `/api/transactions`（クエリ: `main_category_id`, `sub_category_id`, `start_date`, `end_date`）
- POST `/api/transactions`（新規作成）
- PATCH `/api/transactions/<id>`（部分更新）
- DELETE `/api/transactions/<id>`（削除）
 - GET `/api/sub_categories`（クエリ: `main_category_id`, `q` ライブ検索）
 - POST `/api/sub_categories`（小カテゴリの新規作成）
 - PATCH `/api/sub_categories/<id>`（小カテゴリの名前・大カテゴリ更新）
- DELETE `/api/sub_categories/<id>`（小カテゴリ削除・関連取引も削除）
 すべての変更系APIはユーザーの `aikotoba_id` と一致するデータのみに作用（テナント越境を防止）。

認証ガード
- `@app.before_request` でガード。未認証時は `/login` へ。
- API への未認証アクセスは `401 Unauthorized`（JSON）を返す。
- 例外: `/static/*`, `/login`, `/login/line`, `/callback/line`, `/` は許可。

---
この AGENTS.md は「最新の“作業の仕方”」をまとめる場所です。変更がユーザー体験や運用に影響する場合、README と併せて本書も更新してください。

## Flaskアプリケーションへの移行

本プロジェクトは、Streamlitベースの家計簿アプリケーションをFlaskフレームワークに移行しました。これにより、より汎用的なWebアプリケーションとしての利用が可能になります。

### 技術スタックの変更
- **旧:** Python 3.12 / Streamlit / SQLite
- **新:** Python 3.12 / Flask / Jinja2 / SQLite / Bootstrap / Custom CSS / JavaScript

### 主要ファイル/ディレクトリの変更
- `app.py` (Streamlitエントリポイント) から `flask_app.py` (Flaskエントリポイント) へ移行。
- `kakeibo/pages/` (Streamlitページ) のロジックを `flask_app.py` 内のルーティング関数と `templates/` ディレクトリ内のJinja2テンプレートに再構築。
- `templates/` ディレクトリを新規作成し、HTMLテンプレートを配置。
- `static/` ディレクトリを新規作成し、カスタムCSSファイルを配置。

### UI/UXの変更
- Streamlitの組み込みUIコンポーネントを、HTMLフォーム、Bootstrap、カスタムCSS、JavaScript（動的な要素用）で再実装。
- Google Fonts (Noto Sans JP) と Material Icons を導入し、UIの視覚的洗練を実施。

### 機能ごとの実装詳細
- **ホーム (`/`)**: `追加 (/add)` へリダイレクト。
- **追加 (`/add`)**: 取引データの追加フォーム。大カテゴリ連動の小カテゴリ選択。
- **編集 (`/edit`)**: 取引データの一覧表示、フィルター機能（大カテゴリ、小カテゴリ、日付範囲、ライブフィルター）。個別の取引の編集 (`/edit/<id>`) および削除 (`/delete/<id>`)。
- **カテゴリー追加・編集 (`/categories`)**: Tabulator によるスプレッドシート風 UI。インライン編集・行追加・削除・ライブ検索・ページング。従来の個別編集 (`/categories/edit/<id>`) も互換のため残置。
- **グラフ (`/graphs`)**: 月次収支と累計資産のグラフ表示。AltairでJSONを生成し、Vega-Lite.jsで描画。
- **開発者オプション (`/dev`)**: データベースファイルのダウンロード (`/download_db`)、任意のSQL実行機能。

### Docker対応
- Flaskアプリケーション用の`Dockerfile.flask`および`start-flask.sh`を作成し、Dockerでのビルドと実行を可能に。`makefile`にショートカットを追加。

## ToDoリスト（Flask版）

以下の機能はStreamlit版に存在しますが、Flask版では未実装または簡素化されています。
- **サイドバーからの未入力月額のインタラクティブな追加:** Streamlit版ではサイドバーから直接、未入力の定期取引の金額入力と追加が可能でしたが、Flask版では一覧表示のみで、追加は「追加」ページで行う必要があります。
- **認証機能:** Streamlit版に存在するDBログイン、LINEログインなどの認証機能は、Flask版では未実装です。
- **ログアウトボタンの機能:** ログアウトボタンは設置されていますが、機能は未実装です。
- **Google Sheets/Gemini連携:** Streamlit版でもコメントアウトされていましたが、Flask版でも未実装です。

### フロントエンド資産の構成（指針）
- JS は基本的に `static/js/` に配置し、テンプレート内のインライン `<script>` は避ける。
  - ページ固有の JS は `base.html` の `{% block scripts %}` で読み込む（例: `graphs.html` → `graphs.js`）。
  - サーバー生成のデータは `<script type="application/json" id="...">{...}</script>` に埋め込み、JS 側で `JSON.parse` して利用する。
- 共通 UI は `templates/partials/` に切り出して `{% include %}` で再利用（例: `partials/sidebar.html`）。
- CSS は `static/css/` に置き、必要に応じてコンポーネント単位へ分割可。

### 最近のUI/UX更新（要約）
- サイドバーをオフキャンバス化し、開閉ボタン（`>`/`×`）を追加。ナビゲーションはドロップダウン化。リンククリックで自動クローズ。
- 「月の選択」と「予算進捗」を全ページ上部のカードに移設（`templates/partials/top_progress.html`）。折りたたみトグル対応（▲/▼）。
- ルート `/` は `add` にリダイレクト。サイドバーの「ホーム」は `add` を指す。
- カテゴリー管理を編集ページ同等のスプレッドシート UX に刷新。対応する JSON API を追加（上記参照）。

### 2025-08-13 テーマ切替（UI）
- 目的: 青（既定）、ピンク、オレンジ、緑、スレートのカラーテーマをUIから選択可能に。
- 実装:
  - CSS: `static/css/style.css` に `data-theme` ごとのCSS変数セットを追加（`blue/pink/orange/green/slate`）。
  - UI: サイドバー下部にスウォッチ（円形ボタン）を表示（`partials/sidebar.html`）。
  - JS: `static/js/theme.js` で `localStorage('ui_theme')` に保存し、`<html data-theme="...">` を切り替え。初期値は `blue`。

### 2025-08-13 TASK-001（UI）
- 追加: stickyな月次ヘッダーを導入（左右月移動ボタン＋スワイプ対応）。
- 表示: 残額、予測着地、日割り許容額、進捗バーを表示。
- 実装:
  - サーバ: `utils/budget.py` に `month_context()` を追加。`flask_app.get_sidebar_data()` で当月の合計予算/支出を集計し、`month_ctx` としてテンプレへ提供。
  - テンプレ: `templates/partials/month_header.html` を新設し、`base.html` 先頭にインクルード。
  - JS: `static/js/month-nav.js` で `month` クエリに基づく前後月遷移とモバイルスワイプを実装。
- 備考: URLパラメータは既存仕様に合わせ `month=YYYY-MM` を維持。進捗バーは最大100%で安全に丸め。月移動ボタンは「前の月へ」「次の月へ」と明示テキストに変更し、44px最小タップ領域を確保。

### 2025-08-13 TASK-002（UI）
- 目的: 一覧の金額等幅・カテゴリ色/アイコン固定表示で可読性を改善。
- スキーマ: `main_categories`/`sub_categories` に `color TEXT DEFAULT '#64748b'` と `icon TEXT DEFAULT '💡'` を追加（`ensure_aikotoba_schema()` 内で不足時自動付与）。
- API: `/api/transactions` に大カテゴリの `main_color`/`main_icon` を追加（`JOIN main_categories`）。
- API: `/api/main_categories`（GET/PATCH）を追加し、名称・色・アイコンをUIから編集可能に。
- フロント: `templates/edit_list.html` のTabulator列を調整。
  - 金額列: `formatter`で3桁区切り＋`tabular-nums`、`type`に応じて色分け（収入=緑、支出=赤）。
  - 小カテゴリ列: 大カテゴリの色/アイコンを使用したピル＋名称を表示（編集は従来通りセレクト）。
- カテゴリーUI: `templates/categories_list.html` に大カテゴリ編集カードを追加し、`static/js/categories.js` でTabulatorにより `name/color/icon` を直接編集。
- スタイル: `static/css/style.css` に `.amount-cell`, `.cat-pill`, `.cat-name` を追加。

### 2025-08-13 TASK-003（UI）
- 目的: 入力フローの無摩擦化（MRUピル、Enter遷移、金額フォーマット）。
- 追加: `static/js/input-flow.js` を追加し、追加画面の入力順（金額→カテゴリ→日付→メモ）にEnterで遷移、MRU 3件のカテゴリピル表示（localStorage）、金額のリアルタイム3桁区切り（送信時は数値化）。
- テンプレ: `templates/add.html` にMRUエリア（`#mruCats`）を追加、IDを `amount/category/date/memo` に整理し、スクリプトを読み込み。
- 適用拡張: `templates/edit_transaction.html` にも同フロー（MRU表示、Enter遷移、金額フォーマット）を適用。サーバ側も同様に金額を正規化して更新。
- サーバ: `/add` POSTで `amount` を数値化して保存（カンマ等の装飾を除去）。

### 2025-08-13 TASK-004（分析）
- 目的: グラフを見なくても“何が増減したか”を一読で把握。
- サーバ: `services/insights.py` を追加し、`build_insights_cards(engine, ym, aid)` でサブカテゴリ別の支出合計を当月・先月・前年同月で集計。`delta_card` で±10%以上のみ自然文カード化し、比較対象の月（例: `先月比（2025-07 vs 2025-08）`）を明示。
- 画面: `/graphs` で対象月（レンジの終了月）を `focus_month` としてカード生成し、カードはグラフの下に表示。クリックで編集一覧に該当サブカテゴリ＋当月日付範囲を付与して遷移。
- 備考: 表示件数は影響の大きい上位6件に絞り、文言は「先月比/前年比（比較月 vs 対象月）: {サブカテゴリ名} ±X%（±¥Y）」の形式。
### 2025-08-13 TASK-005（撤回）
- 理由: 招待/通知の実装によりパフォーマンス劣化が見られたため全面ロールバック。
- 状態: コード・テンプレから招待/QR/SSEを削除。既存DBに `invites`/`events` が残存しても動作に影響なし（新規作成もしない）。
