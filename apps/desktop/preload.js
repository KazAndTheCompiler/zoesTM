// Preload script for Electron production mode
// Sets __ZOESTM_API_BASE__ for file:// protocol to ensure API calls work
if (typeof window !== 'undefined' && window.__ZOESTM_API_BASE__ === undefined && location.protocol === 'file:') {
  window.__ZOESTM_API_BASE__ = 'http://127.0.0.1:8000';
}
