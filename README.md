# 家計簿アプリ

## 説明

これは、家計を管理するためのStreamlitアプリです。ユーザーは、支出、収入、定期契約、特別支出、および旅行の費用を入力できます。また、支出、収入、および資産の傾向のデータ視覚化を提供します。

## インストール

1.  リポジトリをクローンします。
2.  依存関係をインストールします。

    ```
    pip install -r requirements.txt
    ```

    依存関係は次のとおりです。

    ```
    altair==5.4.0
    google==3.0.0
    google-api-core==2.19.1
    google-api-python-client==2.142.0
    google-auth==2.23.2
    google-auth-httplib2==0.2.0
    google-auth-oauthlib==1.1.0
    googleapis-common-protos==1.63.2
    gspread==5.11.3
    matplotlib==3.9.2
    numpy==1.26.4
    oauthlib==3.2.2
    pandas==2.2.2
    pillow==10.4.0
    requests==2.32.3
    requests-oauthlib==2.0.0
    seaborn==0.13.2
    SQLAlchemy==2.0.32
    streamlit==1.35.0
    toml==0.10.2
    uritemplate==4.1.1
    urllib3==2.2.2
    google-auth==2.23.2
    gspread==5.11.3
    pygwalker == 0.4.9.13
    ```

## 使い方

1.  アプリを実行します。

    ```
    streamlit run streamlit_app.py
    ```
2.  ブラウザでアプリを開きます。
3.  サイドバーを使用して、入力フォーム、データ概要、およびデータ削除ページをナビゲートします。
4.  入力フォームページで、データを入力するカテゴリ（支出、収入、定期契約、特別支出、旅行費用、予算、残高）を選択します。
5.  フォームに記入して送信します。
6.  データ概要ページで、表示するデータ（すべてのデータ、資産の傾向、カテゴリの支出、収入の傾向、定期契約の傾向、特別支出の傾向、旅行費用）を選択します。
7.  データ削除ページで、削除する行を選択してフォームを送信します。

## Laravel Backend & Node Frontend

The `backend-laravel` directory contains a minimal API built with Laravel. Basic CRUD endpoints are available for main categories, sub categories and transactions. To start the API server:

```bash
cd backend-laravel
composer install
php artisan migrate --seed
php artisan serve
```

The `migrate --seed` command creates the schema and loads sample categories and
transactions from `kakeibo_data.json`. Run it once when setting up the backend
locally or whenever you want to reset the data.

The JS frontend in `frontend-js` can be launched with Node.js. It communicates with the Laravel API and lets you manage transactions via a browser.

```bash
cd frontend-js
npm install
npm start
```

Open `http://localhost:3000` in your browser while the Laravel backend is running on port `8000`.

The frontend supports filtering transactions by month range and visualizes income, expense and asset trends in a Chart.js graph.

## Testing

Run API tests inside the Laravel directory:

```bash
cd backend-laravel
composer install
php artisan test
```

Run frontend utility tests:

```bash
cd ../frontend-js
npm test
```

