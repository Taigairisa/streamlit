const { useState, useEffect, useRef } = React;

function App() {
  const apiUrl = 'http://localhost:8000/api';

  const [page, setPage] = useState('input');
  const [mainCategories, setMainCategories] = useState([]);
  const [subCategories, setSubCategories] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [form, setForm] = useState({
    main_category_id: '',
    sub_category_id: '',
    date: '',
    type: '支出',
    detail: '',
    amount: ''
  });
  const [editingId, setEditingId] = useState(null);
  const [filter, setFilter] = useState({start:'', end:'', main:'', sub:''});
  const [deleteSelection, setDeleteSelection] = useState([]);
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    fetchCategories();
    fetchTransactions();
  }, []);

  async function fetchCategories() {
    const resMain = await fetch(`${apiUrl}/main_categories`);
    const main = await resMain.json();
    setMainCategories(main);
    const resSub = await fetch(`${apiUrl}/sub_categories`);
    const sub = await resSub.json();
    setSubCategories(sub);
    if (main.length > 0) {
      setForm(f => ({...f, main_category_id: String(main[0].id)}));
      const firstSub = sub.find(sc => sc.main_category_id === main[0].id);
      if (firstSub) setForm(f => ({...f, sub_category_id: String(firstSub.id)}));
    }
  }

  async function fetchTransactions() {
    const res = await fetch(`${apiUrl}/transactions`);
    const data = await res.json();
    setTransactions(data);
  }

  function handleFormChange(e) {
    const { id, value } = e.target;
    setForm(f => ({ ...f, [id]: value }));
  }

  function handleMainChange(e) {
    const val = e.target.value;
    const firstSub = subCategories.find(sc => String(sc.main_category_id) === val);
    setForm(f => ({ ...f, main_category_id: val, sub_category_id: firstSub ? String(firstSub.id) : '' }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const payload = {
      sub_category_id: form.sub_category_id,
      date: form.date,
      type: form.type,
      detail: form.detail,
      amount: form.amount
    };
    if (editingId) {
      await fetch(`${apiUrl}/transactions/${editingId}`, {
        method: 'PUT',
        headers: { 'Content-Type':'application/json', 'Accept':'application/json' },
        body: JSON.stringify(payload)
      });
    } else {
      await fetch(`${apiUrl}/transactions`, {
        method: 'POST',
        headers: { 'Content-Type':'application/json', 'Accept':'application/json' },
        body: JSON.stringify(payload)
      });
    }
    setForm(f => ({...f, date:'', detail:'', amount:''}));
    setEditingId(null);
    fetchTransactions();
  }

  async function deleteTransaction(id) {
    await fetch(`${apiUrl}/transactions/${id}`, { method:'DELETE' });
    fetchTransactions();
  }

  async function editTransaction(id) {
    const res = await fetch(`${apiUrl}/transactions/${id}`);
    const t = await res.json();
    const sub = subCategories.find(sc => sc.id === t.sub_category_id);
    const mainId = sub ? sub.main_category_id : '';
    setForm({
      main_category_id: String(mainId),
      sub_category_id: String(t.sub_category_id),
      date: t.date,
      type: t.type,
      detail: t.detail,
      amount: t.amount
    });
    setEditingId(id);
    setPage('input');
  }

  function filteredTransactions() {
    let list = utils.filterTransactions(transactions, filter.start, filter.end);
    if (filter.main) {
      list = list.filter(t => {
        const sc = subCategories.find(s => s.id === t.sub_category_id);
        return sc && String(sc.main_category_id) === filter.main;
      });
    }
    if (filter.sub) {
      list = list.filter(t => String(t.sub_category_id) === filter.sub);
    }
    return list;
  }

  useEffect(() => {
    if (page !== 'data') return;
    const data = utils.monthlyChartData(filteredTransactions());
    if (chartInstance.current) chartInstance.current.destroy();
    chartInstance.current = new Chart(chartRef.current, {
      type: 'line',
      data: {
        labels: data.months,
        datasets: [
          { label: '収入', data: data.income, borderColor:'green', fill:false },
          { label: '支出', data: data.expense, borderColor:'red', fill:false },
          { label: '資産', data: data.asset, borderColor:'blue', fill:false }
        ]
      }
    });
  }, [transactions, filter, page]);

  function toggleDelete(id, checked) {
    setDeleteSelection(sel => checked ? [...sel, id] : sel.filter(i => i!==id));
  }

  async function bulkDelete() {
    for (const id of deleteSelection) {
      await fetch(`${apiUrl}/transactions/${id}`, { method:'DELETE' });
    }
    setDeleteSelection([]);
    fetchTransactions();
  }

  const inputSubCats = subCategories.filter(sc => String(sc.main_category_id) === form.main_category_id);
  const filterSubCats = subCategories.filter(sc => !filter.main || String(sc.main_category_id) === filter.main);

  return (
    <div>
      <div className="mb-3">
        <label className="form-label">ページ</label>
        <select className="form-select w-auto d-inline-block" value={page} onChange={e => setPage(e.target.value)}>
          <option value="input">入力</option>
          <option value="data">データ</option>
          <option value="delete">削除</option>
        </select>
      </div>

      {page === 'input' && (
        <div>
          <h2>取引追加</h2>
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label">大カテゴリ</label>
              <select id="main_category_id" className="form-select" value={form.main_category_id} onChange={handleMainChange}>
                {mainCategories.map(mc => <option key={mc.id} value={mc.id}>{mc.name}</option>)}
              </select>
            </div>
            <div className="mb-3">
              <label className="form-label">小カテゴリ</label>
              <select id="sub_category_id" className="form-select" value={form.sub_category_id} onChange={handleFormChange}>
                {inputSubCats.map(sc => <option key={sc.id} value={sc.id}>{sc.name}</option>)}
              </select>
            </div>
            <div className="mb-3">
              <label className="form-label">日付</label>
              <input id="date" type="date" className="form-control" value={form.date} onChange={handleFormChange} />
            </div>
            <div className="mb-3">
              <label className="form-label">種別</label>
              <select id="type" className="form-select" value={form.type} onChange={handleFormChange}>
                <option value="支出">支出</option>
                <option value="収入">収入</option>
                <option value="予算">予算</option>
              </select>
            </div>
            <div className="mb-3">
              <label className="form-label">詳細</label>
              <input id="detail" type="text" className="form-control" value={form.detail} onChange={handleFormChange} />
            </div>
            <div className="mb-3">
              <label className="form-label">金額</label>
              <input id="amount" type="number" className="form-control" value={form.amount} onChange={handleFormChange} />
            </div>
            <button type="submit" className="btn btn-primary">{editingId ? '更新' : '追加'}</button>
          </form>
        </div>
      )}

      {page === 'data' && (
        <div>
          <h2>取引一覧</h2>
          <div className="row mb-3">
            <div className="col">
              <label className="form-label">開始月</label>
              <input type="month" className="form-control" value={filter.start} onChange={e => setFilter(f => ({...f, start:e.target.value}))} />
            </div>
            <div className="col">
              <label className="form-label">終了月</label>
              <input type="month" className="form-control" value={filter.end} onChange={e => setFilter(f => ({...f, end:e.target.value}))} />
            </div>
            <div className="col">
              <label className="form-label">大カテゴリ</label>
              <select className="form-select" value={filter.main} onChange={e => setFilter(f => ({...f, main:e.target.value, sub:''}))}>
                <option value="">すべて</option>
                {mainCategories.map(mc => <option key={mc.id} value={mc.id}>{mc.name}</option>)}
              </select>
            </div>
            <div className="col">
              <label className="form-label">小カテゴリ</label>
              <select className="form-select" value={filter.sub} onChange={e => setFilter(f => ({...f, sub:e.target.value}))}>
                <option value="">すべて</option>
                {filterSubCats.map(sc => <option key={sc.id} value={sc.id}>{sc.name}</option>)}
              </select>
            </div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>日付</th>
                <th>大カテゴリ</th>
                <th>小カテゴリ</th>
                <th>種別</th>
                <th>詳細</th>
                <th>金額</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredTransactions().map(t => {
                const sub = subCategories.find(sc => sc.id === t.sub_category_id);
                const main = subCategories.find(sc => sc.id === t.sub_category_id);
                const mainCat = subCategories.find(sc => sc.id === t.sub_category_id);
                const mainName = mainCategories.find(mc => mc.id === (sub ? sub.main_category_id : null));
                return (
                  <tr key={t.id}>
                    <td>{t.date}</td>
                    <td>{mainName ? mainName.name : ''}</td>
                    <td>{sub ? sub.name : ''}</td>
                    <td>{t.type}</td>
                    <td>{t.detail}</td>
                    <td>{t.amount}</td>
                    <td>
                      <button className="btn btn-secondary btn-sm me-1" onClick={() => editTransaction(t.id)}>編集</button>
                      <button className="btn btn-danger btn-sm" onClick={() => deleteTransaction(t.id)}>削除</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <canvas ref={chartRef} height="100"></canvas>
        </div>
      )}

      {page === 'delete' && (
        <div>
          <h2>取引削除</h2>
          <table className="table">
            <thead>
              <tr>
                <th></th>
                <th>日付</th>
                <th>大カテゴリ</th>
                <th>小カテゴリ</th>
                <th>種別</th>
                <th>詳細</th>
                <th>金額</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map(t => {
                const sub = subCategories.find(sc => sc.id === t.sub_category_id);
                const main = mainCategories.find(mc => mc.id === (sub ? sub.main_category_id : null));
                const checked = deleteSelection.includes(t.id);
                return (
                  <tr key={t.id}>
                    <td><input type="checkbox" checked={checked} onChange={e => toggleDelete(t.id, e.target.checked)} /></td>
                    <td>{t.date}</td>
                    <td>{main ? main.name : ''}</td>
                    <td>{sub ? sub.name : ''}</td>
                    <td>{t.type}</td>
                    <td>{t.detail}</td>
                    <td>{t.amount}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <button className="btn btn-danger" onClick={bulkDelete}>選択削除</button>
        </div>
      )}
    </div>
  );
}

ReactDOM.render(<App />, document.getElementById('root'));
