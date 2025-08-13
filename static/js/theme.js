(function(){
  const KEY = 'ui_theme';
  function applyTheme(theme){
    const t = theme || 'blue';
    document.documentElement.setAttribute('data-theme', t);
    try { localStorage.setItem(KEY, t); } catch(_){ }
    // mark active swatch
    document.querySelectorAll('.theme-picker .swatch').forEach(el=>{
      if (el.getAttribute('data-theme') === t) el.classList.add('active'); else el.classList.remove('active');
    });
  }
  // init from storage
  let saved = null;
  try { saved = localStorage.getItem(KEY); } catch(_){ }
  applyTheme(saved || 'blue');
  // bind clicks
  document.addEventListener('click', function(e){
    const sw = e.target.closest('.theme-picker .swatch');
    if (!sw) return;
    const t = sw.getAttribute('data-theme');
    if (t) applyTheme(t);
  });
})();

