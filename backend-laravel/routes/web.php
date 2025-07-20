<?php

use Illuminate\Support\Facades\Route;
use App\Models\MainCategory;
use App\Models\SubCategory;
use App\Models\Transaction;

Route::get('/', function () {
    return view('welcome');
});

Route::get('/api/main_categories', function () {
    return MainCategory::all();
});

Route::get('/api/sub_categories', function () {
    return SubCategory::all();
});

Route::get('/api/transactions', function () {
    return Transaction::all();
});

Route::post('/api/transactions', function () {
    return Transaction::create(request()->all());
});

Route::put('/api/transactions/{transaction}', function (Transaction $transaction) {
    $transaction->update(request()->all());
    return $transaction;
});

Route::delete('/api/transactions/{transaction}', function (Transaction $transaction) {
    $transaction->delete();
    return response()->json(['message' => 'Deleted']);
});