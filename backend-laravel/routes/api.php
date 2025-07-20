<?php

use Illuminate\Support\Facades\Route;
use App\Models\MainCategory;
use App\Models\SubCategory;
use App\Models\Transaction;
use Illuminate\Http\Request;

Route::get('/main_categories', function () {
    return MainCategory::all();
});

Route::get('/main_categories/{mainCategory}', function (MainCategory $mainCategory) {
    return $mainCategory;
});

Route::post('/main_categories', function (Request $request) {
    return MainCategory::create($request->all());
});

Route::put('/main_categories/{mainCategory}', function (MainCategory $mainCategory, Request $request) {
    $mainCategory->update($request->all());
    return $mainCategory;
});

Route::delete('/main_categories/{mainCategory}', function (MainCategory $mainCategory) {
    $mainCategory->delete();
    return response()->json(['message' => 'Deleted']);
});

Route::get('/sub_categories', function () {
    return SubCategory::all();
});

Route::get('/sub_categories/{subCategory}', function (SubCategory $subCategory) {
    return $subCategory;
});

Route::post('/sub_categories', function (Request $request) {
    return SubCategory::create($request->all());
});

Route::put('/sub_categories/{subCategory}', function (SubCategory $subCategory, Request $request) {
    $subCategory->update($request->all());
    return $subCategory;
});

Route::delete('/sub_categories/{subCategory}', function (SubCategory $subCategory) {
    $subCategory->delete();
    return response()->json(['message' => 'Deleted']);
});

Route::get('/transactions', function () {
    return Transaction::all();
});

Route::get('/transactions/{transaction}', function (Transaction $transaction) {
    return $transaction;
});

Route::post('/transactions', function () {
    return Transaction::create(request()->all());
});

Route::put('/transactions/{transaction}', function (Transaction $transaction) {
    $transaction->update(request()->all());
    return $transaction;
});

Route::delete('/transactions/{transaction}', function (Transaction $transaction) {
    $transaction->delete();
    return response()->json(['message' => 'Deleted']);
});

Route::get('/month-summary/{month}', function ($month) {
    $summary = Transaction::selectRaw('sub_categories.name as sub_category_name, type, SUM(amount) as total')
        ->join('sub_categories', 'transactions.sub_category_id', '=', 'sub_categories.id')
        ->join('main_categories', 'sub_categories.main_category_id', '=', 'main_categories.id')
        ->where('main_categories.name', '日常')
        ->where('transactions.date', 'like', "$month%")
        ->groupBy('sub_category_name', 'type')
        ->get();

    $budget = $summary->where('type', '予算')->pluck('total', 'sub_category_name');
    $spent = $summary->where('type', '支出')->pluck('total', 'sub_category_name');
    return ['spent' => $spent, 'budget' => $budget];
});
