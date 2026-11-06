/* IntelliWatts client-side theme: explicit preference overrides the OS setting. */
(() => {
  'use strict';
  const key = 'intelliwatts-theme';
  const allowed = ['light', 'dark', 'system'];
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = 'system';
  try {
    const stored = window.localStorage.getItem(key);
    if (allowed.includes(stored)) preference = stored;
  } catch (_) { /* Private browsing may deny access; use OS preference. */ }

  const resolved = () => preference === 'system' ? (media.matches ? 'dark' : 'light') : preference;
  function update() {
    const mode = resolved();
    document.documentElement.dataset.theme = mode;
    document.documentElement.style.colorScheme = mode;
    const button = document.getElementById('theme-toggle');
    if (button) {
      const dark = mode === 'dark';
      button.setAttribute('aria-pressed', String(dark));
      button.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
      button.title = dark ? 'Switch to light mode' : 'Switch to dark mode';
    }
    document.dispatchEvent(new CustomEvent('iw-theme-change', {detail:{mode}}));
    return mode;
  }
  window.IWTheme = {
    get mode() { return resolved(); },
    get preference() { return preference; },
    set(value) {
      if (!allowed.includes(value)) return;
      preference = value;
      try { window.localStorage.setItem(key, preference); } catch (_) { /* no-op */ }
      update();
    },
    toggle() { this.set(resolved() === 'dark' ? 'light' : 'dark'); },
    update
  };
  update();
  media.addEventListener?.('change', () => { if (preference === 'system') update(); });
  document.addEventListener('DOMContentLoaded', update);
})();
