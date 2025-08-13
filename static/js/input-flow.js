// Input flow enhancements for Add page
document.addEventListener('DOMContentLoaded', () => {
  // Enter to next focus order
  const order = ['amount', 'category', 'date', 'memo'];
  order.forEach((id, i) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const next = document.getElementById(order[i + 1]);
        if (next) next.focus();
        else document.querySelector('form#entry')?.requestSubmit?.();
      }
    });
  });

  // MRU recent categories
  const KEY = 'mru_categories';
  function mruSet(id, name) {
    try {
      const raw = localStorage.getItem(KEY) || '[]';
      const arr = JSON.parse(raw).filter((x) => String(x.id) !== String(id));
      arr.unshift({ id, name });
      localStorage.setItem(KEY, JSON.stringify(arr.slice(0, 3)));
    } catch (_) {}
  }
  function mruRender() {
    const wrap = document.getElementById('mruCats');
    if (!wrap) return;
    let html = '';
    try {
      const mru = JSON.parse(localStorage.getItem(KEY) || '[]');
      html = mru
        .map((c) => `<button type="button" class="pill" data-id="${c.id}" data-name="${c.name}">${c.name}</button>`)
        .join('');
    } catch (_) {}
    wrap.innerHTML = html;
    wrap.querySelectorAll('button.pill').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        const name = btn.getAttribute('data-name') || '';
        const sel = document.getElementById('category');
        if (sel) { sel.value = id; mruSet(id, name); sel.dispatchEvent(new Event('change')); }
      });
    });
  }
  mruRender();

  // Amount formatting live
  const amt = document.getElementById('amount');
  const nf = new Intl.NumberFormat('ja-JP');
  amt?.addEventListener('input', () => {
    const raw = (amt.value || '').replace(/[^\d\-]/g, '');
    if (!raw) { amt.value = ''; return; }
    const num = Number(raw);
    if (!Number.isNaN(num)) amt.value = nf.format(num);
  });

  // Submit sanitization and MRU update
  document.querySelector('form#entry')?.addEventListener('submit', () => {
    if (amt) amt.value = (amt.value || '').replace(/[^\d\-]/g, '');
    const sel = document.getElementById('category');
    const opt = sel ? sel.options[sel.selectedIndex] : null;
    if (opt) mruSet(opt.value, opt.textContent || '');
  });
});

