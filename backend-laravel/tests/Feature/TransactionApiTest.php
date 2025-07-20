<?php

namespace Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;
use App\Models\MainCategory;
use App\Models\SubCategory;
use App\Models\Transaction;

class TransactionApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_crud_flow(): void
    {
        $main = MainCategory::create(['name' => 'Daily']);
        $sub = $main->subCategories()->create(['name' => 'Food']);

        $data = [
            'sub_category_id' => $sub->id,
            'amount' => 100,
            'type' => '支出',
            'date' => '2025-01-01',
            'detail' => 'test detail',
        ];

        $create = $this->post('/api/transactions', $data);
        $create->assertStatus(200);
        $this->assertDatabaseHas('transactions', ['detail' => 'test detail']);

        $id = Transaction::first()->id;

        $update = $this->put("/api/transactions/{$id}", ['detail' => 'updated']);
        $update->assertStatus(200)
               ->assertJsonFragment(['detail' => 'updated']);
        $this->assertDatabaseHas('transactions', ['id' => $id, 'detail' => 'updated']);

        $delete = $this->delete("/api/transactions/{$id}");
        $delete->assertStatus(200);
        $this->assertDatabaseMissing('transactions', ['id' => $id]);
    }

    public function test_monthly_summary_endpoint(): void
    {
        $main = MainCategory::create(['name' => '日常']);
        $sub = $main->subCategories()->create(['name' => 'Food']);

        Transaction::create([
            'sub_category_id' => $sub->id,
            'amount' => 50,
            'type' => '支出',
            'date' => '2025-07-01',
        ]);

        Transaction::create([
            'sub_category_id' => $sub->id,
            'amount' => 200,
            'type' => '予算',
            'date' => '2025-07-01',
        ]);

        $response = $this->get('/api/month-summary/2025-07');
        $response->assertStatus(200)
                 ->assertJson([
                     'spent' => ['Food' => 50],
                     'budget' => ['Food' => 200],
                 ]);
    }
}
