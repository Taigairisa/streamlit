(function(root, factory){
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.utils = factory();
  }
}(this, function(){
  function filterTransactions(transactions, startMonth, endMonth) {
    return transactions.filter(t => {
      const m = t.date.slice(0,7);
      if (startMonth && m < startMonth) return false;
      if (endMonth && m > endMonth) return false;
      return true;
    });
  }

  function monthlyChartData(transactions) {
    const map = {};
    transactions.forEach(t => {
      const month = t.date.slice(0,7);
      if (!map[month]) map[month] = {income:0, expense:0};
      if (t.type === '収入') map[month].income += Number(t.amount);
      if (t.type === '支出') map[month].expense += Number(t.amount);
    });
    const months = Object.keys(map).sort();
    const income = [];
    const expense = [];
    const asset = [];
    let acc = 0;
    months.forEach(m => {
      const i = map[m].income;
      const e = map[m].expense;
      income.push(i);
      expense.push(e);
      acc += i - e;
      asset.push(acc);
    });
    return {months, income, expense, asset};
  }

  return {filterTransactions, monthlyChartData};
}));

