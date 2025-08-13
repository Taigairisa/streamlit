// Lightweight editable grid for Transactions (Edit tab)
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

  const tbl = document.getElementById('transactionsTable');
  if (!tbl) return;

  const tbody = tbl.querySelector('tbody');
  tbl.addEventListener('touchstart', (e) => { e.preventDefault(); });
  const alertArea = document.getElementById('alertArea');
  const tableInfo = document.getElementById('tableInfo');
  const addBtn = document.getElementById('addRowBtn');
  const applyBtn = document.getElementById('applyBtn');
  const reloadBtn = document.getElementById('reloadBtn');
  const dirtyBadge = document.getElementById('dirtyBadge');

  const mainSel = document.getElementById('mainCategorySelect');
  const subSel = document.getElementById('subCategorySelect');
  const startDate = document.getElementById('startDate');
  const endDate = document.getElementById('endDate');
  const liveFilter = document.getElementById('liveFilter');

  const prevPageBtn = document.getElementById('prevPageBtn');
  const nextPageBtn = document.getElementById('nextPageBtn');
  const pageSizeSelect = document.getElementById('pageSizeSelect');

  const subJson = document.getElementById('subCategoriesData');
  const allSub = subJson ? JSON.parse(subJson.textContent||'[]') : [];
  const subOptionsByMain = {}; const subToMain = {}; const subName = {};
  for (const [sid, mid, name] of allSub){
    if (!subOptionsByMain[mid]) subOptionsByMain[mid] = [];
    subOptionsByMain[mid].push([sid, name]);
    subToMain[sid] = mid; subName[sid] = name;
  }

  function showAlert(msg, type='warning', timeout=3000){
    alertArea.innerHTML = `<div class="alert alert-${type} py-2" role="alert">${msg}</div>`;
    if (timeout) setTimeout(()=> alertArea.innerHTML='', timeout);
  }
  function buildApiUrl(){
    const url = new URL('/api/transactions', window.location.origin);
    if (mainSel.value) url.searchParams.set('main_category_id', mainSel.value);
    if (subSel.value) url.searchParams.set('sub_category_id', subSel.value);
    if (startDate.value) url.searchParams.set('start_date', startDate.value);
    if (endDate.value) url.searchParams.set('end_date', endDate.value);
    const q = (liveFilter.value||'').trim(); if (q) url.searchParams.set('q', q); // Add live filter query
    url.searchParams.set('limit', pageSize);
    url.searchParams.set('offset', currentPage * pageSize);
    return url.toString();
  }
  function updateSubFilter(){
    const mid = parseInt(mainSel.value||'0',10);
    subSel.innerHTML = '';
    (subOptionsByMain[mid]||[]).forEach(([sid,name])=>{
      const o = document.createElement('option'); o.value=sid; o.textContent=name; subSel.appendChild(o);
    });
  }

  let originalById = new Map();
  let rows = [];
  let deleted = new Set();
  let tempIdSeq = -1;
  function markDirty(){ dirtyBadge.hidden = computeDiffSummary().total===0; }

  async function load(){
    try{
      const r = await fetch(buildApiUrl(), {cache:'no-store'});
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json(); // Assuming data is { items: [...], total_count: N }
      const list = data.items;
      const totalCount = data.total_count;

      originalById.clear();
      rows = list.map(x=>({ id:x.id, date:x.date, detail:x.detail||'', type:x.type, amount: x.amount, sub_category_id: x.sub_category_id }));
      rows.forEach(r=> originalById.set(r.id, JSON.parse(JSON.stringify(r))));
      deleted.clear();
      render();
      tableInfo.textContent = `${(currentPage * pageSize) + 1}-${(currentPage * pageSize) + rows.length} / ${totalCount} 件表示`;
      
      // Enable/disable pagination buttons
      prevPageBtn.disabled = (currentPage === 0);
      nextPageBtn.disabled = ((currentPage + 1) * pageSize >= totalCount);

      markDirty();
    }catch(e){ showAlert('読み込みに失敗しました: '+e.message,'danger',5000); }
  }

  function render(){
    tbody.innerHTML='';
    const mid = parseInt(mainSel.value||'0',10);
    const subChoices = subOptionsByMain[mid]||[];
    const nf = new Intl.NumberFormat('ja-JP');
    rows.forEach(r=>{
      if (deleted.has(r.id)) return;
      const tr = document.createElement('tr'); tr.dataset.rowId = String(r.id);

      // ID
      const tdId = document.createElement('td'); tdId.textContent = String(r.id>0? r.id : ''); tr.appendChild(tdId);
      // Date
      const tdDate = document.createElement('td'); const inDate = document.createElement('input'); inDate.type='date'; inDate.className='form-control form-control-sm'; inDate.value=r.date||''; inDate.addEventListener('change',()=>{ r.date=inDate.value; markDirty(); }); tdDate.appendChild(inDate); tr.appendChild(tdDate);
      // Detail
      const tdDet = document.createElement('td'); const inDet = document.createElement('input'); inDet.type='text'; inDet.className='form-control form-control-sm'; inDet.value=r.detail||''; inDet.addEventListener('input',()=>{ r.detail=inDet.value; markDirty(); }); tdDet.appendChild(inDet); tr.appendChild(tdDet);
      // Type
      const tdType = document.createElement('td'); const selT = document.createElement('select'); selT.className='form-select form-select-sm'; ['支出','収入','予算'].forEach(t=>{ const o=document.createElement('option'); o.value=t; o.textContent=t; selT.appendChild(o); }); selT.value=r.type||'支出'; selT.addEventListener('change',()=>{ r.type=selT.value; markDirty(); }); tdType.appendChild(selT); tr.appendChild(tdType);
      // Amount
      const tdAmt = document.createElement('td'); const inAmt = document.createElement('input'); inAmt.type='text'; inAmt.inputMode='numeric'; inAmt.className='form-control form-control-sm'; inAmt.value = (r.amount!=null)? nf.format(r.amount):''; inAmt.addEventListener('input',()=>{ const raw=(inAmt.value||'').replace(/[^\d\-]/g,''); if(!raw){ r.amount=null; inAmt.value=''; markDirty(); return;} const num=Number(raw); if(!Number.isNaN(num)){ inAmt.value=nf.format(num); r.amount=num; markDirty(); } }); tdAmt.appendChild(inAmt); tr.appendChild(tdAmt);
      // Sub-category
      const tdSub = document.createElement('td'); const selS=document.createElement('select'); selS.className='form-select form-select-sm'; subChoices.forEach(([sid,name])=>{ const o=document.createElement('option'); o.value=sid; o.textContent=name; selS.appendChild(o); }); selS.value = r.sub_category_id || (subChoices[0]?.[0]||''); selS.addEventListener('change',()=>{ r.sub_category_id=parseInt(selS.value,10); markDirty(); }); tdSub.appendChild(selS); tr.appendChild(tdSub);
      // Ops
      const tdOps = document.createElement('td'); const delBtn=document.createElement('button'); delBtn.type='button'; delBtn.className='btn btn-sm btn-outline-danger'; delBtn.textContent='削除'; delBtn.addEventListener('click',()=>{ if(!confirm('削除としてマークします。よろしいですか？')) return; if(r.id>0){ deleted.add(r.id);} else { rows=rows.filter(x=>x!==r);} render(); markDirty(); }); tdOps.appendChild(delBtn); tr.appendChild(tdOps);

      tbody.appendChild(tr);
    });
  }

  function addRow(){
    const today = new Date().toISOString().slice(0,10);
    const mid = parseInt(mainSel.value||'0',10);
    const sid = (subOptionsByMain[mid]||[])[0]?.[0] || null;
    rows.unshift({ id: tempIdSeq--, date: today, detail:'', type:'支出', amount:0, sub_category_id: sid });
    render(); markDirty();
  }

  function computeDiffSummary(){
    const creates=[]; const updates=[]; const deletes=[]; const changedRows=[];
    for (const r of rows){
      if (r.id>0){
        if (deleted.has(r.id)) { deletes.push(r.id); changedRows.push({type:'delete', before: originalById.get(r.id)||{id:r.id} }); continue; }
        const o = originalById.get(r.id)||{}; const payload={};
        ['date','detail','type','amount','sub_category_id'].forEach(k=>{ if ((o[k]??'') !== (r[k]??'')) payload[k] = r[k]; });
        if (Object.keys(payload).length){ updates.push({id:r.id, payload}); changedRows.push({type:'update', id:r.id, before:o, after:r}); }
      } else {
        if (!deleted.has(r.id)){
          if (r.sub_category_id && r.date && r.type && r.amount!=null){ creates.push({ sub_category_id:r.sub_category_id, date:r.date, type:r.type, amount:r.amount, detail:r.detail||'' }); changedRows.push({type:'create', after:r}); }
        }
      }
    }
    for (const id of deleted){ if (!deletes.includes(id)) { deletes.push(id); changedRows.push({type:'delete', before: originalById.get(id)||{id}}); } }
    return { creates, updates, deletes, changedRows, total: creates.length+updates.length+deletes.length };
  }

  function buildSummaryHtml(diff){
    const nf = new Intl.NumberFormat('ja-JP');
    const fieldLabel = { date:'日付', detail:'詳細', type:'種別', amount:'金額', sub_category_id:'小カテゴリ' };
    const lines=[];
    if (diff.creates.length) lines.push(`<li>新規作成: ${diff.creates.length} 件</li>`);
    if (diff.updates.length) lines.push(`<li>更新: ${diff.updates.length} 件</li>`);
    if (diff.deletes.length) lines.push(`<li>削除: ${diff.deletes.length} 件</li>`);
    const blocks=[];
    diff.changedRows.forEach(ch=>{
      if (ch.type==='create'){
        const a=ch.after; blocks.push(`<div class="mb-2"><b>作成:</b> ${a.date} ${a.type} ¥${nf.format(a.amount||0)} [${subName[a.sub_category_id]||a.sub_category_id}] ${a.detail||''}</div>`);
      } else if (ch.type==='update'){
        const items=[]; const b=ch.before; const a=ch.after;
        for (const k of Object.keys(ch.after)){
          if (k==='id') continue;
        }
        if ((b.date||'') !== (a.date||'')) items.push(`<li>${fieldLabel.date}: ${b.date||''} → ${a.date||''}</li>`);
        if ((b.detail||'') !== (a.detail||'')) items.push(`<li>${fieldLabel.detail}: ${(b.detail||'')} → ${(a.detail||'')}</li>`);
        if ((b.type||'') !== (a.type||'')) items.push(`<li>${fieldLabel.type}: ${b.type||''} → ${a.type||''}</li>`);
        if ((b.amount??'') !== (a.amount??'')) items.push(`<li>${fieldLabel.amount}: ¥${nf.format(b.amount||0)} → ¥${nf.format(a.amount||0)}</li>`);
        if ((b.sub_category_id||'') !== (a.sub_category_id||'')) items.push(`<li>${fieldLabel.sub_category_id}: ${(subName[b.sub_category_id]||b.sub_category_id||'')} → ${(subName[a.sub_category_id]||a.sub_category_id||'')}</li>`);
        blocks.push(`<div class="mb-2"><b>更新 #${ch.id}:</b><ul>${items.join('')}</ul></div>`);
      } else if (ch.type==='delete'){
        const b=ch.before; blocks.push(`<div class="mb-2"><b>削除 #${b.id}:</b> ${b.date||''} ${b.type||''} ¥${nf.format(b.amount||0)} [${subName[b.sub_category_id]||b.sub_category_id||''}] ${b.detail||''}</div>`);
      }
    });
    return `<ul>${lines.join('')}</ul>${blocks.join('')}`;
  }

  async function applyChanges(){
    const diff = computeDiffSummary();
    if (diff.total===0){ showAlert('変更はありません。','info'); return; }
    const modalEl = document.getElementById('txApplyModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    document.getElementById('txApplySummary').innerHTML = buildSummaryHtml(diff);
    modal.show();
    const btn = document.getElementById('txApplyConfirmBtn');
    const onClick = async ()=>{
      btn.disabled = true;
      try{
        for (const c of diff.creates){
          const r = await fetch('/api/transactions', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(c)});
          if(!r.ok) throw new Error(await r.text());
        }
        for (const u of diff.updates){
          const r = await fetch(`/api/transactions/${u.id}`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify(u.payload)});
          if(!r.ok) throw new Error(await r.text());
        }
        for (const id of diff.deletes){
          const r = await fetch(`/api/transactions/${id}`, {method:'DELETE'});
          if(!r.ok) throw new Error(await r.text());
        }
        modal.hide(); showAlert('変更を適用しました。','success',2000); load();
      }catch(e){ showAlert('適用に失敗しました: '+e.message,'danger',5000); }
      finally{ btn.disabled=false; btn.removeEventListener('click', onClick); }
    };
    btn.addEventListener('click', onClick);
    modalEl.addEventListener('hidden.bs.modal', ()=>{ btn.removeEventListener('click', onClick); }, {once:true});
  }

  function ensureNoLoseChanges(next){
    if (computeDiffSummary().total>0){ if(!confirm('未保存の変更があります。破棄して続行しますか？')) return; }
    next();
  }

  // Wire
  addBtn.addEventListener('click', addRow);
  applyBtn.addEventListener('click', applyChanges);
  reloadBtn.addEventListener('click', ()=> ensureNoLoseChanges(load));
  mainSel.addEventListener('change', ()=>{ updateSubFilter(); debouncedLoad(); });
  subSel.addEventListener('change', ()=> debouncedLoad());
  startDate.addEventListener('change', ()=> debouncedLoad());
  endDate.addEventListener('change', ()=> debouncedLoad());
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

  // Init filters + load
  updateSubFilter();
  load();
});

