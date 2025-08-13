(function(){
  function ensureHost(){
    let h = document.getElementById('toastHost');
    if(!h){ h = document.createElement('div'); h.id='toastHost'; h.className='toast-host'; document.body.appendChild(h); }
    return h;
  }
  function showToast(text, actions, timeout){
    const h = ensureHost();
    const t = document.createElement('div'); t.className='toast';
    t.innerHTML = `<div class="body">${escapeHtml(text||'')}</div>`;
    if(Array.isArray(actions) && actions.length){
      const ac = document.createElement('div'); ac.className='actions';
      actions.forEach(a=>{ const b=document.createElement('button'); b.textContent=a.label||'OK'; b.addEventListener('click',()=>{ try{a.onClick&&a.onClick();}catch(_){ } dismiss(); }); ac.appendChild(b); });
      t.appendChild(ac);
    }
    h.appendChild(t);
    requestAnimationFrame(()=> t.classList.add('show'));
    const kill = setTimeout(dismiss, timeout||2500);
    function dismiss(){ clearTimeout(kill); t.classList.remove('show'); setTimeout(()=> t.remove(), 200); }
    return dismiss;
  }
  function pulseRow(el){ try{ el.classList.add('pulse'); setTimeout(()=> el.classList.remove('pulse'), 1000);}catch(_){}}
  function escapeHtml(s){ return (s||'').replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[m])); }
  window.MOTION = { showToast, pulseRow };
})();

