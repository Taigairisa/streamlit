// Categories page: spreadsheet-like UX using Tabulator with fallback
document.addEventListener('DOMContentLoaded', function () {
  const gridEl = document.getElementById('categoriesGrid');
  if (!gridEl) return;

  const mainSel = document.getElementById('catMainSelect');
  const liveFilter = document.getElementById('catLiveFilter');
  const pageSizeSel = document.getElementById('catPageSize');
  const infoEl = document.getElementById('catTableInfo');
  const alertArea = document.getElementById('catAlertArea');
  const addRowBtn = document.getElementById('catAddRowBtn');
  const reloadBtn = document.getElementById('catReloadBtn');
  const undoBtn = document.getElementById('catUndoBtn');
  const redoBtn = document.getElementById('catRedoBtn');

  const mainCatsJson = document.getElementById('mainCategoriesData');
  const mainCategories = mainCatsJson ? JSON.parse(mainCatsJson.textContent || '[]') : [];
  const mainOptions = Object.fromEntries(mainCategories.map(c => [String(c[0]), c[1]]));

  function showAlert(message, type = 'warning', timeout = 3000) {
    alertArea.innerHTML = `<div class="alert alert-${type} py-2" role="alert">${message}</div>`;
    if (timeout) setTimeout(() => (alertArea.innerHTML = ''), timeout);
  }

  function buildApiUrl() {
    const url = new URL('/api/sub_categories', window.location.origin);
    if (mainSel.value) url.searchParams.set('main_category_id', mainSel.value);
    if (liveFilter.value.trim()) url.searchParams.set('q', liveFilter.value.trim());
    return url.toString();
  }

  let table = null;

  // Presets
  const COLOR_PRESETS = {
    '#64748b': 'Slate',
    '#3b82f6': 'Blue',
    '#ec4899': 'Pink',
    '#f97316': 'Orange',
    '#10b981': 'Green',
    '#ef4444': 'Red',
    '#8b5cf6': 'Purple',
    '#14b8a6': 'Teal',
    '#f59e0b': 'Amber',
  };
  const ICON_PRESETS = {
    '💡': '電気/光熱','🍔': '外食','🛒': '食料品','🚃': '交通','🚗': '自動車','🏠': '住居','📱': '通信','🏥': '医療','🎉': '娯楽','🧾': '税金','💳': 'カード','📦': '通販','🧺': '日用品','🍽️': '食事','🍼': '育児','💼': '仕事','🏫': '教育','🐾': 'ペット','🎁': '贈与',
    '💰': '貯金','🧠': '学習','🏃': '運動','🧘': '健康','⚽': 'スポーツ','🎮': 'ゲーム','🎬': '映画','🎧': '音楽','📚': '書籍','✈️': '旅行','🧳': '旅費','⛽': 'ガソリン','🪑': '家具','🖥️': '家電','🥗': 'サラダ','🍣': '寿司','🍺': 'ビール','🍷': 'ワイン','☕': 'コーヒー','🍞': 'パン','🍰': 'スイーツ','💊': '薬','🧧': '祝儀','🐶': '犬','🐱': '猫','🧴':'化粧品','🧹':'掃除','🧽':'消耗品','🏖️':'レジャー','🚌':'バス','🚕':'タクシー','🚲':'自転車','🛏️':'寝具','🔧':'修理','🗂️':'サブスク'
  };

  // List editor item formatter helpers (for Tabulator 'list' editor)
  function colorItemFormatter(value, text){
    return `<span class="swatch-dot" style="background:${value}"></span>`;
  }
  function iconItemFormatter(value, text){
    return `<span style="font-size:1.1rem; line-height:1;">${value}</span>`;
  }

  // Custom editors to show swatches/icons instead of text list
  function colorEditor(cell, onRendered, success, cancel){
    const wrap = document.createElement('div');
    wrap.className = 'preset-menu';
    Object.keys(COLOR_PRESETS).forEach(code => {
      const btn = document.createElement('button');
      btn.type = 'button'; btn.className = 'preset-item color';
      btn.style.background = code; btn.title = COLOR_PRESETS[code] || code;
      btn.addEventListener('click', ()=> success(code));
      wrap.appendChild(btn);
    });
    onRendered(()=> wrap.focus());
    wrap.tabIndex = 0;
    wrap.addEventListener('keydown', (e)=>{ if(e.key==='Escape'){ cancel(); } });
    return wrap;
  }

  function iconEditor(cell, onRendered, success, cancel){
    const wrap = document.createElement('div');
    wrap.className = 'preset-menu';
    Object.keys(ICON_PRESETS).forEach(icon => {
      const btn = document.createElement('button');
      btn.type = 'button'; btn.className = 'preset-item icon';
      btn.textContent = icon; btn.title = ICON_PRESETS[icon] || '';
      btn.addEventListener('click', ()=> success(icon));
      wrap.appendChild(btn);
    });
    onRendered(()=> wrap.focus());
    wrap.tabIndex = 0;
    wrap.addEventListener('keydown', (e)=>{ if(e.key==='Escape'){ cancel(); } });
    return wrap;
  }

  function buildTable() {
    const pageSize = parseInt(pageSizeSel.value || '50', 10);
    table = new Tabulator(gridEl, {
      layout: 'fitColumns',
      responsiveLayout: 'hide', // Added responsive layout
      height: '600px',
      selectable: true,
      clipboard: true,
      history: true,
      pagination: pageSize > 0 ? 'local' : false,
      paginationSize: pageSize > 0 ? pageSize : undefined,
      ajaxURL: buildApiUrl(),
      ajaxContentType: 'json',
      columns: [
        { title: 'ID', field: 'id', width: 80, hozAlign: 'right', headerHozAlign: 'right', sorter: 'number' },
        {
          title: '大カテゴリ',
          field: 'main_category_id',
          hozAlign: 'left',
          headerHozAlign: 'left',
          editor: 'list',
          editorParams: { values: mainOptions },
          formatter: function (cell) {
            const v = String(cell.getValue() || '');
            return mainOptions[v] || v;
          },
        },
        { title: '小カテゴリ名', field: 'name', editor: 'input', minWidth: 160 },
        { title: '色', field: 'color', editor: 'list', editorParams: { values: COLOR_PRESETS, itemFormatter: colorItemFormatter, listItemFormatter: colorItemFormatter }, minWidth: 140,
          formatter: function (cell) {
            const v = cell.getValue() || '#64748b';
            return `<span class="swatch-dot" style="background:${v}"></span>`;
          }
        },
        { title: 'アイコン', field: 'icon', editor: 'list', editorParams: { values: ICON_PRESETS, itemFormatter: iconItemFormatter, listItemFormatter: iconItemFormatter }, minWidth: 120,
          formatter: function (cell) {
            const v = cell.getValue() || '💡';
            return `<span style="font-size:1rem;">${v}</span>`;
          }
        },
        {
          title: '操作', field: 'ops', headerSort: false, width: 120, hozAlign: 'center',
          formatter: function () { return '<button class="btn btn-sm btn-danger">削除</button>'; },
          cellClick: function (e, cell) {
            const data = cell.getRow().getData();
            if (!data.id) return;
            if (!confirm('本当に削除しますか？このカテゴリに紐づく取引も削除されます。')) return;
            fetch(`/api/sub_categories/${data.id}`, { method: 'DELETE' })
              .then(async r => { if (!r.ok) throw new Error(await r.text()); return r.json(); })
              .then(() => { cell.getRow().delete(); showAlert('削除しました。', 'success', 1500); })
              .catch(err => showAlert('削除に失敗しました: ' + err.message, 'danger', 5000));
          }
        }
      ],
      dataLoaded: function (data) {
        infoEl.textContent = `${data.length} 件表示`;
      }
    });

    table.on('cellEdited', function (cell) {
      const row = cell.getRow();
      const data = row.getData();
      const field = cell.getField();
      const newVal = data[field];
      const oldVal = typeof cell.getOldValue === 'function' ? cell.getOldValue() : undefined;
      if (oldVal === newVal) return;
      const col = cell.getColumn();
      const title = col && col.getDefinition ? (col.getDefinition().title || field) : field;
      const ok = confirm(`以下を変更します:\n${title}: ${oldVal ?? ''} → ${newVal ?? ''}\n保存してよろしいですか？`);
      if (!ok) {
        try { if (typeof cell.restoreOldValue === 'function') cell.restoreOldValue(); else cell.setValue(oldVal, true); } catch (_) {}
        return;
      }
      const payload = { [field]: newVal };
      if (data.id) {
        fetch(`/api/sub_categories/${data.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
          .then(r => { if (!r.ok) showAlert('更新に失敗しました', 'danger'); });
      } else {
        tryCreateRow(row);
      }
    });

    table.on('rowAdded', function (row) {
      const data = row.getData();
      if (!data.id) tryCreateRow(row);
    });
  }

  // main categories editor removed

  function tryCreateRow(row) {
    const data = row.getData();
    const mid = data.main_category_id || (mainSel.value ? parseInt(mainSel.value, 10) : undefined);
    const name = data.name || '';
    if (!mid || !name.trim()) { showAlert('大カテゴリと小カテゴリ名を入力してください。'); return; }
    const summary = `新規作成します:\n大カテゴリ: ${mainOptions[String(mid)] || mid}\n小カテゴリ: ${name}\n保存してよろしいですか？`;
    if (!confirm(summary)) return;
    fetch('/api/sub_categories', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ main_category_id: mid, name }) })
      .then(async r => { if (!r.ok) throw new Error(await r.text()); return r.json(); })
      .then(j => { if (j.id) { row.update({ id: j.id }); showAlert('保存しました。', 'success', 1500); } })
      .catch(err => showAlert('保存に失敗しました: ' + err.message, 'danger', 5000));
  }

  function reloadTable() { if (table) table.setData(buildApiUrl()); }

  // Wire controls
  addRowBtn.addEventListener('click', function () { table.addRow({ main_category_id: mainSel.value || '' }); });
  reloadBtn.addEventListener('click', reloadTable);
  undoBtn.addEventListener('click', function () { if (table) table.undo(); });
  redoBtn.addEventListener('click', function () { if (table) table.redo(); });
  mainSel.addEventListener('change', reloadTable);
  liveFilter.addEventListener('input', function () { reloadTable(); });
  pageSizeSel.addEventListener('change', function () { if (table) { const data = table.getData(); table.destroy(); buildTable(); table.setData(data); } });

  // Initialize
  if (window.Tabulator) buildTable();
  else {
    const check = setInterval(() => { if (window.Tabulator) { clearInterval(check); buildTable(); } }, 100);
    setTimeout(() => clearInterval(check), 5000);
  }
});
