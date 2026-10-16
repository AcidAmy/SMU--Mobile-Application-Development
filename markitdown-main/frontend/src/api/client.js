/**
 * Axios HTTP Client with JWT interceptors.
 * Supports window.axios (from CDN) or imported axios.
 */
import { config } from '../config.js';

// Resolve axios instance (support browser global CDN or ES module)
const axiosLib = window.axios || (await import('https://cdn.jsdelivr.net/npm/axios@1.7.9/+esm')).default;

export const apiClient = axiosLib.create({
  timeout: 120000, // 2 minutes for large PDF OCR
});

// Dynamic baseURL resolution
apiClient.interceptors.request.use(
  (reqConfig) => {
    // If request URL is relative, prepend API_BASE_URL
    if (!reqConfig.url.startsWith('http://') && !reqConfig.url.startsWith('https://')) {
      reqConfig.baseURL = config.API_BASE_URL;
    }

    // Attach JWT Bearer Token if available
    const token = localStorage.getItem(config.STORAGE_KEYS.TOKEN);
    if (token) {
      reqConfig.headers = reqConfig.headers || {};
      reqConfig.headers.Authorization = `Bearer ${token}`;
    }

    return reqConfig;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for unified error formatting and 401 handling
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response ? error.response.status : null;
    let message = error.message;

    if (error.response && error.response.data) {
      const data = error.response.data;
      if (typeof data.detail === 'string') {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        message = data.detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
      } else if (data.message) {
        message = data.message;
      }
    }

    // Handle token expiration / unauthorized
    if (status === 401) {
      const hadToken = !!localStorage.getItem(config.STORAGE_KEYS.TOKEN);
      localStorage.removeItem(config.STORAGE_KEYS.TOKEN);
      localStorage.removeItem(config.STORAGE_KEYS.USER);
      window.dispatchEvent(new CustomEvent('auth:expired', { detail: { hadToken } }));
    }

    return Promise.reject({
      status,
      message,
      original: error,
    });
  }
);

export default apiClient;
