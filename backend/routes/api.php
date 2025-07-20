<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ItemController;

Route::middleware('api')->group(function () {
    Route::apiResource('items', ItemController::class);
});
