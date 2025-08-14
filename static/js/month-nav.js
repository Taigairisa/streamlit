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
  let touchStartX = 0;
  let touchStartY = 0;

  function isScrollable(element) {
    if (!element) return false;
    const style = window.getComputedStyle(element);
    const hasScroll = ['auto', 'scroll'].includes(style.overflowX) || 
                      ['auto', 'scroll'].includes(style.overflowY);
    if (hasScroll) return true;
    
    // Check if element has actual scroll
    return element.scrollWidth > element.clientWidth || 
           element.scrollHeight > element.clientHeight;
  }

  window.addEventListener('touchstart', (e) => {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  }, { passive: true });

  window.addEventListener('touchend', (e) => {
    const target = e.target;
    const touchEndX = e.changedTouches[0].clientX;
    const touchEndY = e.changedTouches[0].clientY;
    
    // Calculate horizontal and vertical movement
    const dx = touchEndX - touchStartX;
    const dy = touchEndY - touchStartY;
    
    // Check if the gesture is primarily horizontal
    // (horizontal movement is greater than vertical movement)
    const isHorizontalGesture = Math.abs(dx) > Math.abs(dy);
    
    // Check if the touch originated from an interactive element or form
    const isInteractiveOrFormElement = target.matches('input, select, textarea, button, a') || 
                                     target.closest('form');

    // Check if any parent element is scrollable
    let element = target;
    let hasScrollableParent = false;
    while (element && element !== document.body) {
      if (isScrollable(element)) {
        hasScrollableParent = true;
        break;
      }
      element = element.parentElement;
    }

    // Only trigger month navigation if:
    // 1. The gesture is primarily horizontal
    // 2. The touch is not on an interactive element
    // 3. The element is not inside a scrollable container
    // 4. The horizontal movement is significant enough (> 60px)
    if (isHorizontalGesture && 
        !isInteractiveOrFormElement && 
        !hasScrollableParent && 
        Math.abs(dx) > 60) {
      gotoMonth(dx < 0 ? 1 : -1);
    }
  }, { passive: true });

  updateMonthNavButtons(); // Call on initial load
});

