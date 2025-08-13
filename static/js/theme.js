(function(){
  const KEY = 'ui_theme';
  const KEY_MODE = 'ui_mode';
  function applyTheme(theme){
    const t = theme || 'blue';
    document.documentElement.setAttribute('data-theme', t);
    try { localStorage.setItem(KEY, t); } catch(_){ }
    document.querySelectorAll('.theme-picker .swatch').forEach(el=>{
      if (el.getAttribute('data-theme') === t) el.classList.add('active'); else el.classList.remove('active');
    });
  }
  function applyMode(mode){
    const m = mode === 'dark' ? 'dark' : 'light';
    if (m === 'dark') document.documentElement.setAttribute('data-mode', 'dark');
    else document.documentElement.removeAttribute('data-mode');
    try { localStorage.setItem(KEY_MODE, m); } catch(_){ }
    const toggle = document.getElementById('themeDarkToggle');
    if (toggle) toggle.checked = (m === 'dark');
  }
  // init from storage
  let saved = null, savedMode = null;
  try { saved = localStorage.getItem(KEY); savedMode = localStorage.getItem(KEY_MODE); } catch(_){ }
  applyTheme(saved || 'blue');
  applyMode(savedMode || 'light');
  // bind clicks
  document.addEventListener('click', function(e){
    const sw = e.target.closest('.theme-picker .swatch');
    if (sw) {
      const t = sw.getAttribute('data-theme');
      if (t) applyTheme(t);
    }
  });
  document.addEventListener('change', function(e){
    const chk = e.target.closest('#themeDarkToggle');
    if (chk) {
      applyMode(chk.checked ? 'dark' : 'light');
    }
  });
})();
