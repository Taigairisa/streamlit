# Backend Setup

This directory contains a minimal Laravel application used by the project.

## Setup

1. Install PHP (>=8.1) and Composer.
2. Run `composer install` inside this directory.
3. Copy `.env.example` to `.env` and adjust your database credentials.
4. Generate an application key:

   ```
   php artisan key:generate
   ```

5. Run database migrations:

   ```
   php artisan migrate
   ```

## Example `.env`

```env
APP_NAME=Laravel
APP_ENV=local
APP_KEY=
APP_DEBUG=true
APP_URL=http://localhost

DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=laravel
DB_USERNAME=root
DB_PASSWORD=
```
