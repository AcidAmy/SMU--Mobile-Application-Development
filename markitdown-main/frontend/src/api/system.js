/**
 * System Health and Backend status API module.
 */
import apiClient from './client.js';

export const systemApi = {
  /**
   * Check backend health and plugin availability
   */
  async getHealth() {
    return apiClient.get('/health');
  },
};
