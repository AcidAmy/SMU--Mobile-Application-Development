/**
 * Authentication API module using JWT.
 */
import apiClient from './client.js';
import { config } from '../config.js';

export const authApi = {
  /**
   * Log in with username and password using JSON endpoint
   */
  async login(username, password) {
    const res = await apiClient.post('/auth/login-json', { username, password });
    if (res.access_token) {
      localStorage.setItem(config.STORAGE_KEYS.TOKEN, res.access_token);
      if (res.user) {
        localStorage.setItem(config.STORAGE_KEYS.USER, JSON.stringify(res.user));
      }
    }
    return res;
  },

  /**
   * Register a new user
   */
  async register(username, password, email = null) {
    const payload = { username, password };
    if (email && email.trim()) {
      payload.email = email.trim();
    }
    return apiClient.post('/auth/register', payload);
  },

  /**
   * Get current authenticated user profile
   */
  async getProfile() {
    return apiClient.get('/auth/me');
  },

  /**
   * Log out and clear local credentials
   */
  logout() {
    localStorage.removeItem(config.STORAGE_KEYS.TOKEN);
    localStorage.removeItem(config.STORAGE_KEYS.USER);
  },

  /**
   * Check if token is locally stored
   */
  hasToken() {
    return !!localStorage.getItem(config.STORAGE_KEYS.TOKEN);
  },

  /**
   * Get cached user info if available
   */
  getCachedUser() {
    try {
      const u = localStorage.getItem(config.STORAGE_KEYS.USER);
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  }
};
