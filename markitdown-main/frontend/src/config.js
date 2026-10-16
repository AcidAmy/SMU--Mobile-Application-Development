/**
 * MarkItDown Frontend Configuration
 * Manages API endpoint resolution and local storage keys.
 */

const STORAGE_KEYS = {
  TOKEN: 'markitdown_jwt_token',
  USER: 'markitdown_user',
  API_URL: 'markitdown_api_base_url',
};

// Automatically detect API Base URL
function getInitialApiBaseUrl() {
  const saved = localStorage.getItem(STORAGE_KEYS.API_URL);
  if (saved) return saved;

  // In local development or standalone preview:
  const port = window.location.port;
  const hostname = window.location.hostname || '127.0.0.1';

  // If served on backend port (e.g. 8000), use relative /api
  if (port === '8000') {
    return '/api';
  }

  // Otherwise default to the FastAPI backend at http://127.0.0.1:8000/api
  return `http://${hostname}:8000/api`;
}

export const config = {
  API_BASE_URL: getInitialApiBaseUrl(),
  STORAGE_KEYS,
  setApiBaseUrl(newUrl) {
    this.API_BASE_URL = newUrl.replace(/\/+$/, '');
    localStorage.setItem(STORAGE_KEYS.API_URL, this.API_BASE_URL);
  },
  resetApiBaseUrl() {
    localStorage.removeItem(STORAGE_KEYS.API_URL);
    this.API_BASE_URL = getInitialApiBaseUrl();
  }
};
