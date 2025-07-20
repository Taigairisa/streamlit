const assert = require('assert');
const { filterTransactions, monthlyChartData } = require('./utils');

const data = [
  { date: '2025-07-01', type: '収入', amount: 100, sub_category_id: 1 },
  { date: '2025-07-02', type: '支出', amount: 50, sub_category_id: 1 },
  { date: '2025-08-01', type: '支出', amount: 30, sub_category_id: 1 }
];

const filtered = filterTransactions(data, '2025-07', '2025-07');
assert.strictEqual(filtered.length, 2);

const chart = monthlyChartData(filtered);
assert.deepStrictEqual(chart.months, ['2025-07']);
assert.deepStrictEqual(chart.income, [100]);
assert.deepStrictEqual(chart.expense, [50]);
console.log('utils tests passed');

