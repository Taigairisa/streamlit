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

  function buildTable() {
    const pageSize = parseInt(pageSizeSel.value || '50', 10);
    table = new Tabulator(gridEl, {
      layout: 'fitColumns',
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
          editor: 'select',
          editorParams: { values: mainOptions },
          formatter: function (cell) {
            const v = String(cell.getValue() || '');
            return mainOptions[v] || v;
          },
        },
        { title: '小カテゴリ名', field: 'name', editor: 'input' },
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
    // Try load from CDN tags already present
    const check = setInterval(() => { if (window.Tabulator) { clearInterval(check); buildTable(); } }, 100);
    setTimeout(() => clearInterval(check), 5000);
  }
});

