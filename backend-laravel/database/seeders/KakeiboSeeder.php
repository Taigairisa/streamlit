<?php

namespace Database\Seeders;

use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use App\Models\MainCategory;
use App\Models\SubCategory;
use App\Models\Transaction;
use App\Models\BackupTime;

class KakeiboSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $json = file_get_contents(base_path('../kakeibo_data.json'));
        $data = json_decode($json, true);

        DB::statement('PRAGMA foreign_keys = OFF;');

        MainCategory::truncate();
        SubCategory::truncate();
        Transaction::truncate();
        BackupTime::truncate();

        foreach ($data['main_categories'] as $mainCategory) {
            MainCategory::create($mainCategory);
        }

        foreach ($data['sub_categories'] as $subCategory) {
            SubCategory::create($subCategory);
        }

        foreach ($data['transactions'] as $transaction) {
            Transaction::create($transaction);
        }

        foreach ($data['backup_time'] as $backupTime) {
            BackupTime::create($backupTime);
        }

        DB::statement('PRAGMA foreign_keys = ON;');
    }
}