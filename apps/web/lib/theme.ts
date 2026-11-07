export const THEME_STORAGE_KEY = "nodetrail-theme-v1";

// Apply the preference before first paint, independently of React hydration.
export const themeBootstrap = `(() => {
  let saved = null;
  try { saved = localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)}); } catch {}
  const explicit = saved === 'dark' || saved === 'light';
  const theme = explicit ? saved : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.dataset.theme = theme;
  document.documentElement.dataset.themePreference = explicit ? 'user' : 'system';
  document.documentElement.style.colorScheme = theme;
})();`;
