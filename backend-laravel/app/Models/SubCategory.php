<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class SubCategory extends Model
{
    protected $guarded = [];

    public function mainCategory()
    {
        return $this->belongsTo(MainCategory::class);
    }

    public function transactions()
    {
        return $this->hasMany(Transaction::class);
    }
}
