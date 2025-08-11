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
- `static/`: カスタム CSS（Bootstrap/Google Fonts/CDN を併用）。
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
- 予算進捗: サイドバーで選択した月のプログレス（URLの`month`を全ページで維持）。
- 贈与見える化: 「贈与」小カテゴリの収入/支出の対比。
- 未入力の月額: 定期カテゴリの未入力リマインド。
- グラフ: 月次収支/累計資産（開始/終了月フィルタ対応）。
- 編集: スプレッドシート風 UI（Tabulator）。セル編集/行追加/削除、ソート、ライブ検索。変更時は「旧→新」の確認ダイアログ。CDN不可時は簡易表へフォールバック。
- 開発者オプション: DB ダウンロード（`/download_db`）、任意 SQL 実行（例外表示）。
- LINE ログイン: `GET /login/line` → `GET /callback/line`（最小実装）。`/logout` でセッションクリア。

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
- **ホーム (`/`)**: メインカテゴリ選択とサイドバー表示。
- **追加 (`/add`)**: 取引データの追加フォーム。大カテゴリ連動の小カテゴリ選択。
- **編集 (`/edit`)**: 取引データの一覧表示、フィルター機能（大カテゴリ、小カテゴリ、日付範囲、ライブフィルター）。個別の取引の編集 (`/edit/<id>`) および削除 (`/delete/<id>`)。
- **カテゴリー追加・編集 (`/categories`)**: 小カテゴリの追加、既存小カテゴリのリネーム (`/categories/edit/<id>`)、削除 (`/categories/delete/<id>`)。
- **グラフ (`/graphs`)**: 月次収支と累計資産のグラフ表示。AltairでJSONを生成し、Vega-Lite.jsで描画。
- **開発者オプション (`/dev`)**: データベースファイルのダウンロード (`/download_db`)、任意のSQL実行機能。

### Docker対応
- Flaskアプリケーション用の`Dockerfile.flask`および`start-flask.sh`を作成し、Dockerでのビルドと実行を可能に。`makefile`にショートカットを追加。

## ToDoリスト（Flask版）

以下の機能はStreamlit版に存在しますが、Flask版では未実装または簡素化されています。
- **開発者オプションのバグ:** 現在のflask_app.pyでは開発者オプションにアクセスするとInternalServerErrorになります。
- **編集ページでの表形式の直接編集機能:** Streamlitの`st.data_editor`のような、表内で直接データの追加・更新・削除を行う機能は実装されていません。個別フォームでの編集・削除となっています。
- **サイドバーからの未入力月額のインタラクティブな追加:** Streamlit版ではサイドバーから直接、未入力の定期取引の金額入力と追加が可能でしたが、Flask版では一覧表示のみで、追加は「追加」ページで行う必要があります。
- **認証機能:** Streamlit版に存在するDBログイン、LINEログインなどの認証機能は、Flask版では未実装です。
- **ログアウトボタンの機能:** ログアウトボタンは設置されていますが、機能は未実装です。
- **Google Sheets/Gemini連携:** Streamlit版でもコメントアウトされていましたが、Flask版でも未実装です。
