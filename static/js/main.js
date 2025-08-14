// Main JS for global behaviors (sidebar, month selection)
document.addEventListener('DOMContentLoaded', function () {
  const sidebar = document.getElementById('sidebarOffcanvas');
  const openBtn = document.getElementById('sidebarOpenBtn');

  if (sidebar && openBtn && window.bootstrap) {
    const offcanvas = new bootstrap.Offcanvas(sidebar, { scroll: true, backdrop: true });

    sidebar.addEventListener('shown.bs.offcanvas', function () {
      openBtn.classList.add('d-none');
    });
    sidebar.addEventListener('hidden.bs.offcanvas', function () {
      openBtn.classList.remove('d-none');
    });

    // Auto-close sidebar when a navigation item is clicked
    sidebar.addEventListener('click', function (e) {
      const a = e.target.closest('a');
      if (!a) return;
      // Ignore dropdown toggle clicks
      if (a.classList.contains('dropdown-toggle')) return;
      // Only act on real navigation links
      if (a.matches('.dropdown-item, .nav-link') && a.getAttribute('href')) {
        try { offcanvas.hide(); } catch (_) {}
      }
    });
  }

  // Month selector: keep month param across pages
  const monthSelect = document.getElementById('monthSelect');
  if (monthSelect) {
    monthSelect.addEventListener('change', function () {
      const url = new URL(window.location.href);
      const params = url.searchParams;
      params.set('month', this.value);
      url.search = params.toString();
      window.location.href = url.toString();
    });
  }

  // Top progress collapse toggle arrow
  const topCollapse = document.getElementById('topProgressCollapse');
  const topToggle = document.getElementById('topProgressToggle');
  if (topCollapse && topToggle) {
    const updateArrow = () => {
      const expanded = topCollapse.classList.contains('show');
      topToggle.textContent = expanded ? '▲' : '▼';
    };
    topCollapse.addEventListener('shown.bs.collapse', updateArrow);
    topCollapse.addEventListener('hidden.bs.collapse', updateArrow);
    // Initial
    updateArrow();
  }
});

// Helper to generate a consistent color from a string (e.g., category name)
function generateColorFromString(str) {
  if (!str) return '#64748b'; // Default color for empty/null string
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
    hash |= 0; // Ensure 32bit integer
  }
  const hue = Math.abs(hash % 360);
  return `hsl(${hue}, 70%, 50%)`;
}