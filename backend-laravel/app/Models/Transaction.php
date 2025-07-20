<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Transaction extends Model
{
    protected $guarded = [];

    protected $fillable = ['sub_category_id', 'amount', 'type', 'date', 'detail'];

    public function subCategory()
    {
        return $this->belongsTo(SubCategory::class);
    }
}
