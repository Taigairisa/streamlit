function gotoMonth(offset) {
  const url = new URL(location.href);
  const paramName = 'month';
  const ym = (url.searchParams.get(paramName) || document.body.dataset.currentYm || '').split('-').map(Number);
  if (!ym[0] || !ym[1]) {
    const now = new Date();
    ym[0] = now.getFullYear();
    ym[1] = now.getMonth() + 1;
  }
  const d = new Date(ym[0], ym[1] - 1 + offset, 1);
  const nextYm = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  url.searchParams.set(paramName, nextYm);
  location.href = url.toString();
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('mPrev')?.addEventListener('click', () => gotoMonth(-1));
  document.getElementById('mNext')?.addEventListener('click', () => gotoMonth(1));
  let sx = 0;
  window.addEventListener('touchstart', (e) => (sx = e.touches[0].clientX), { passive: true });
  window.addEventListener(
    'touchend',
    (e) => {
      const dx = e.changedTouches[0].clientX - sx;
      if (Math.abs(dx) > 60) gotoMonth(dx < 0 ? 1 : -1);
    },
    { passive: true }
  );
});

