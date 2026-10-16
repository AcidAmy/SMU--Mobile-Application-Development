/**
 * Document Conversion and Classification API module.
 */
import apiClient from './client.js';

export const convertApi = {
  /**
   * Upload and convert file with DL routing or force OCR
   */
  async uploadAndConvert(file, options = {}, onProgress = null) {
    const formData = new FormData();
    formData.append('file', file);

    const params = {
      auto_classify: options.autoClassify !== undefined ? options.autoClassify : true,
      force_ocr: options.forceOcr || false,
    };
    if (options.customPrompt) {
      params.custom_prompt = options.customPrompt;
    }

    return apiClient.post('/convert/upload', formData, {
      params,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
  },

  /**
   * Pre-classify file with PyTorch DL model only
   */
  async classifyFile(file, onProgress = null) {
    const formData = new FormData();
    formData.append('file', file);

    return apiClient.post('/classify', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
  },

  /**
   * Convert remote document or web URL with Anti-SSRF protection
   */
  async convertUrl(url, options = {}) {
    return apiClient.post('/convert/url', {
      url,
      auto_classify: options.autoClassify !== undefined ? options.autoClassify : true,
      force_ocr: options.forceOcr || false,
      custom_prompt: options.customPrompt || null,
    });
  },
};
