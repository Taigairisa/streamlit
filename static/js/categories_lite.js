// Lightweight editable table for Categories (no Tabulator)
document.addEventListener('DOMContentLoaded', function(){
  // Debounce helper function
  function debounce(func, delay) {
    let timeout;
    return function(...args) {
      const context = this;
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(context, args), delay);
    };
  }
  const debouncedLoad = debounce(() => ensureNoLoseChanges(load), 750);

  let currentPage = 0;
  let pageSize = 50; // Default page size

  const gridEl = document.getElementById('categoriesGrid');
  if (!gridEl) return;

  const tbl = document.getElementById('categoriesTable');
  const tbody = tbl.querySelector('tbody');
  
  const mainSel = document.getElementById('catMainSelect');
  const liveFilter = document.getElementById('catLiveFilter');
  const infoEl = document.getElementById('catTableInfo');
  const alertArea = document.getElementById('catAlertArea');
  const addBtn = document.getElementById('catAddRowBtn');
  const applyBtn = document.getElementById('catApplyBtn');
  const reloadBtn = document.getElementById('catReloadBtn');
  const dirtyBadge = document.getElementById('catDirtyBadge');

  const prevPageBtn = document.getElementById('catPrevPageBtn');
  const nextPageBtn = document.getElementById('catNextPageBtn');
  const pageSizeSelect = document.getElementById('catPageSizeSelect');

  const mainCatsJson = document.getElementById('mainCategoriesData');
  const mainCategories = mainCatsJson ? JSON.parse(mainCatsJson.textContent || '[]') : [];
  const mainOptions = Object.fromEntries(mainCategories.map(c => [String(c[0]), c[1]])); // This is for main category select options

  const mainColorById = {};
  mainCategories.forEach(([mid, name, color]) => { // mainCategories now contains color
    mainColorById[String(mid)] = color;
  });

  // Simple icon choices (emoji only)
  const ICON_CHOICES = ['💡','🍔','🛒','🚃','🚗','🏠','📱','🏥','🎉','🧾','💳','📦','🧺','🍽️','🍼','💼','🏫','🐾','🎁','💰','🧠','🏃','🧘','⚽','🎮','🎬','🎧','📚','✈️','🧳','⛽','🪑','🖥️','🥗','🍣','🍺','🍷','☕','🍞','🍰','💊','🧧','🐶','🐱','🧴','🧹','🧽','🏖️','🚌','🚕','🚲','🛏️','🔧','🗂️'];

  function showAlert(msg, type='warning', timeout=3000){
    alertArea.innerHTML = `<div class="alert alert-${type} py-2" role="alert">${msg}</div>`;
    if (timeout) setTimeout(()=> alertArea.innerHTML='', timeout);
  }

  function buildApiUrl(){
    const url = new URL('/api/sub_categories', window.location.origin);
    if (mainSel.value) url.searchParams.set('main_category_id', mainSel.value);
    const q = (liveFilter.value||'').trim(); if (q) url.searchParams.set('q', q);
    url.searchParams.set('limit', pageSize);
    url.searchParams.set('offset', currentPage * pageSize);
    return url.toString();
  }

  let originalById = new Map();  // id -> row
  let rows = [];                  // current rows (including new temp rows)
  let deleted = new Set();        // ids marked for deletion
  let tempIdSeq = -1;             // temporary negative id for new rows

  function markDirty(){
    const has = computeDiffSummary().total > 0;
    dirtyBadge.hidden = !has;
  }

  function load(){
    fetch(buildApiUrl(), {cache:'no-store'})
      .then(async r=>{ if(!r.ok) throw new Error(await r.text()); return r.json(); })
      .then(data=>{ // Assuming data is { items: [...], total_count: N }
        const list = data.items;
        const totalCount = data.total_count;

        originalById.clear();
        rows = list.map(r=>({ id:r.id, main_category_id:r.main_category_id, name:r.name, icon: r.icon || '💡' }));
        rows.forEach(r=> originalById.set(r.id, JSON.parse(JSON.stringify(r))));
        deleted.clear();
        render();
        infoEl.textContent = `${(currentPage * pageSize) + 1}-${(currentPage * pageSize) + rows.length} / ${totalCount} 件表示`;
        
        // Enable/disable pagination buttons
        prevPageBtn.disabled = (currentPage === 0);
        nextPageBtn.disabled = ((currentPage + 1) * pageSize >= totalCount);

        markDirty();
      })
      .catch(e=> showAlert('読み込みに失敗しました: '+e.message, 'danger', 5000));
  }

  function render(){
    tbody.innerHTML = '';
    rows.forEach(r=>{
      if (deleted.has(r.id)) return;
      const tr = document.createElement('tr');
      tr.dataset.rowId = String(r.id);

      // ID
      const tdId = document.createElement('td'); tdId.textContent = String(r.id ?? ''); tr.appendChild(tdId);

      // Main category select
      const tdMain = document.createElement('td');
      const sel = document.createElement('select'); sel.className='form-select form-select-sm';
      const emptyOpt = document.createElement('option'); emptyOpt.value=''; emptyOpt.textContent='選択'; sel.appendChild(emptyOpt);
      Object.entries(mainOptions).forEach(([val,label])=>{
        const opt = document.createElement('option'); opt.value = val; opt.textContent = label; sel.appendChild(opt);
      });
      sel.value = String(r.main_category_id || '');
      sel.addEventListener('change', ()=>{ r.main_category_id = sel.value ? parseInt(sel.value,10) : null; markDirty(); });
      tdMain.appendChild(sel); tr.appendChild(tdMain);

      // Name input
      const tdName = document.createElement('td');
      const nameWrapper = document.createElement('div'); // Wrapper for icon and input
      nameWrapper.style.display = 'flex';
      nameWrapper.style.alignItems = 'center';

      const iconSpan = document.createElement('span');
      iconSpan.textContent = r.icon || '';
      const mainColor = mainColorById[String(r.main_category_id)] || '#64748b'; // Get main category color
      iconSpan.style.backgroundColor = mainColor;
      iconSpan.style.color = '#fff'; // White icon color
      iconSpan.style.borderRadius = '50%';
      iconSpan.style.width = '1.5em'; // Slightly larger for visibility
      iconSpan.style.height = '1.5em';
      iconSpan.style.display = 'inline-grid';
      iconSpan.style.placeItems = 'center';
      iconSpan.style.marginRight = '0.5em';
      iconSpan.style.flexShrink = '0'; // Prevent shrinking

      const inp = document.createElement('input');
      inp.type = 'text';
      inp.className = 'form-control form-control-sm';
      inp.value = r.name || ''; // Only name in the input field
      inp.addEventListener('input', () => { r.name = inp.value; markDirty(); });
      inp.style.flexGrow = '1'; // Allow input to grow

      nameWrapper.appendChild(iconSpan);
      nameWrapper.appendChild(inp);
      tdName.appendChild(nameWrapper);
      tr.appendChild(tdName);

      // Icon select
      const tdIcon = document.createElement('td');
      const ico = document.createElement('select'); ico.className='form-select form-select-sm';
      ICON_CHOICES.forEach(ic=>{ const o=document.createElement('option'); o.value=ic; o.textContent=ic; ico.appendChild(o); });
      ico.value = r.icon || ICON_CHOICES[0];
      ico.addEventListener('change', ()=>{ r.icon = ico.value; markDirty(); });
      tdIcon.appendChild(ico); tr.appendChild(tdIcon);

      // Ops
      const tdOps = document.createElement('td');
      tdOps.style.minWidth = '60px';
      const delBtn = document.createElement('button'); delBtn.type='button'; delBtn.className='btn btn-sm btn-outline-danger'; delBtn.textContent='削除';
      delBtn.addEventListener('click', ()=>{
        if (!confirm('削除としてマークします。よろしいですか？')) return;
        if (r.id && r.id > 0) { deleted.add(r.id); } else {
          // new row not yet saved -> remove from array
          rows = rows.filter(x=>x!==r);
        }
        render(); markDirty();
      });
      tdOps.appendChild(delBtn); tr.appendChild(tdOps);

      tbody.appendChild(tr);
    });
  }

  function addRow(){
    rows.unshift({ id: tempIdSeq--, main_category_id: mainSel.value ? parseInt(mainSel.value,10) : null, name:'', icon: ICON_CHOICES[0] });
    render(); markDirty();
  }

  function computeDiffSummary(){
    const creates = [];
    const updates = [];
    const deletes = [];
    const changedRows = [];

    for (const r of rows){
      if (r.id && r.id > 0){
        if (deleted.has(r.id)) { deletes.push(r.id); continue; }
        const orig = originalById.get(r.id);
        if (!orig) continue;
        const payload = {};
        if (orig.main_category_id !== r.main_category_id) payload.main_category_id = r.main_category_id;
        if ((orig.name||'') !== (r.name||'')) payload.name = r.name || '';
        if ((orig.icon||'') !== (r.icon||'')) payload.icon = r.icon || '';
        if (Object.keys(payload).length){ updates.push({ id: r.id, payload }); changedRows.push({type:'update', id:r.id, after:r}); }
      } else {
        // new temp row, if not marked delete and minimally valid
        if (!deleted.has(r.id)){
          if (r.main_category_id && (r.name||'').trim()){
            creates.push({ main_category_id: r.main_category_id, name: r.name.trim(), icon: r.icon || '' });
            changedRows.push({type:'create', tempId: r.id, after:r});
          }
        }
      }
    }
    for (const id of deleted){ deletes.push(id); changedRows.push({type:'delete', id}); }

    return { creates, updates, deletes, changedRows, total: creates.length + updates.length + deletes.length };
  }

  function buildSummaryHtml(diff){
    const fieldLabel = { main_category_id:'大カテゴリ', name:'小カテゴリ名', icon:'アイコン' };
    function labelMain(id){ return mainOptions[String(id)] || id; }
    function fmtRow(r){ return `[${labelMain(r.main_category_id)}] ${r.name || ''} ${r.icon || ''}`; }

    const lines = [];
    if (diff.creates.length) lines.push(`<li>新規作成: ${diff.creates.length} 件</li>`);
    if (diff.updates.length) lines.push(`<li>更新: ${diff.updates.length} 件</li>`);
    if (diff.deletes.length) lines.push(`<li>削除: ${diff.deletes.length} 件</li>`);

    const blocks = [];
    // Creates details
    diff.creates.forEach((c, i)=>{
      blocks.push(`<div class="mb-2"><b>作成 ${i+1}:</b> ${fmtRow(c)}</div>`);
    });
    // Updates with field-level diffs
    diff.updates.forEach((u, i)=>{
      const before = originalById.get(u.id) || {};
      const after = rows.find(r=>r.id===u.id) || {};
      const items = [];
      for (const k of Object.keys(u.payload)){
        const oldVal = (k==='main_category_id') ? labelMain(before[k]) : (before[k]||'');
        const newVal = (k==='main_category_id') ? labelMain(after[k]) : (after[k]||'');
        items.push(`<li>${fieldLabel[k]||k}: ${oldVal} → ${newVal}</li>`);
      }
      blocks.push(`<div class="mb-2"><b>更新 #${u.id}:</b><ul>${items.join('')}</ul></div>`);
    });
    // Deletes details
    diff.deletes.forEach((id)=>{
      const r = originalById.get(id) || {id};
      blocks.push(`<div class="mb-2"><b>削除 #${id}:</b> ${fmtRow(r)}</div>`);
    });

    return `<ul>${lines.join('')}</ul>${blocks.join('') || ''}` || '<div>変更はありません。</div>';
  }

  async function applyChanges(){
    const diff = computeDiffSummary();
    if (diff.total === 0){ showAlert('変更はありません。','info'); return; }
    const modalEl = document.getElementById('applyConfirmModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    document.getElementById('applySummary').innerHTML = buildSummaryHtml(diff);
    modal.show();

    const confirmBtn = document.getElementById('applyConfirmBtn');
    const onClick = async ()=>{
      confirmBtn.disabled = true;
      try{
        // Creates
        for (const c of diff.creates){
          const r = await fetch('/api/sub_categories', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(c)});
          if(!r.ok) throw new Error(await r.text());
        }
        // Updates
        for (const u of diff.updates){
          const r = await fetch(`/api/sub_categories/${u.id}`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify(u.payload)});
          if(!r.ok) throw new Error(await r.text());
        }
        // Deletes
        for (const id of diff.deletes){
          const r = await fetch(`/api/sub_categories/${id}`, {method:'DELETE'});
          if(!r.ok) throw new Error(await r.text());
        }
        modal.hide();
        showAlert('変更を適用しました。','success', 2000);
        load();
      }catch(e){ showAlert('適用に失敗しました: '+e.message,'danger',5000); }
      finally{ confirmBtn.disabled = false; confirmBtn.removeEventListener('click', onClick); }
    };
    confirmBtn.addEventListener('click', onClick);
    modalEl.addEventListener('hidden.bs.modal', ()=>{ confirmBtn.removeEventListener('click', onClick); }, {once:true});
  }

  function ensureNoLoseChanges(next){
    if (computeDiffSummary().total>0){
      if (!confirm('未保存の変更があります。破棄して続行しますか？')) return;
    }
    next();
  }

  // Wire controls
  addBtn.addEventListener('click', ()=> addRow());
  applyBtn.addEventListener('click', applyChanges);
  reloadBtn.addEventListener('click', ()=> ensureNoLoseChanges(load));
  mainSel.addEventListener('change', ()=> debouncedLoad());
  liveFilter.addEventListener('input', ()=> debouncedLoad());

  prevPageBtn.addEventListener('click', ()=>{
    if (currentPage > 0) {
      currentPage--;
      ensureNoLoseChanges(load);
    }
  });
  nextPageBtn.addEventListener('click', ()=>{
    currentPage++; // Optimistically increment, load will correct if out of bounds
    ensureNoLoseChanges(load);
  });
  pageSizeSelect.addEventListener('change', ()=>{
    pageSize = parseInt(pageSizeSelect.value, 10);
    currentPage = 0; // Reset to first page when page size changes
    ensureNoLoseChanges(load);
  });
  
  
  

  // Initial
  load();
});
