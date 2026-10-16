/**
 * Conversion History Records API module.
 */
import apiClient from './client.js';

export const recordsApi = {
  /**
   * List history conversion records
   */
  async getRecords(skip = 0, limit = 50) {
    return apiClient.get('/records', {
      params: { skip, limit },
    });
  },

  /**
   * Get single conversion record with complete markdown content
   */
  async getRecordDetail(recordId) {
    return apiClient.get(`/records/${recordId}`);
  },

  /**
   * Delete a conversion record (for owner)
   */
  async deleteRecord(recordId) {
    return apiClient.delete(`/records/${recordId}`);
  },
};
