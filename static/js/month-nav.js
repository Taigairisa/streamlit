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
  // After navigation, the page will reload, and updateMonthNavButtons will be called on DOMContentLoaded
  // So no need to call it here directly after location.href
}

function updateMonthNavButtons() {
  const today = new Date();
  const currentYm = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
  const displayedYm = document.body.dataset.currentYm;
  const availableMonths = JSON.parse(document.body.dataset.availableMonths || '[]');

  const mNextBtn = document.getElementById('mNext');
  if (mNextBtn) {
    mNextBtn.disabled = (displayedYm === currentYm);
  }

  const mPrevBtn = document.getElementById('mPrev');
  if (mPrevBtn && availableMonths.length > 0) {
    const oldestYm = availableMonths[availableMonths.length - 1];
    mPrevBtn.disabled = (displayedYm === oldestYm);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('mPrev')?.addEventListener('click', () => gotoMonth(-1));
  document.getElementById('mNext')?.addEventListener('click', () => gotoMonth(1));
  let sx = 0;
  window.addEventListener('touchstart', (e) => (sx = e.touches[0].clientX), { passive: true });
  window.addEventListener(
    'touchend',
    (e) => {
      const target = e.target;
      // Check if the touch originated from an interactive form element, inside a form, or inside a scrollable container
      const isInteractiveOrFormElement = target.matches('input, select, textarea, button, a') || target.closest('form');
      const isScrollableContainer = target.closest('[style*="overflow-x: scroll"], [style*="overflow-x: auto"], [style*="overflow: scroll"], [style*="overflow: auto"]');

      if (isInteractiveOrFormElement || isScrollableContainer) {
        // If touch originated inside an interactive element, a form, or a scrollable area,
        // assume it's for element interaction or scrolling, and do not trigger month navigation.
        return;
      }

      const dx = e.changedTouches[0].clientX - sx;
      if (Math.abs(dx) > 60) gotoMonth(dx < 0 ? 1 : -1);
    },
    { passive: true }
  );

  updateMonthNavButtons(); // Call on initial load
});

