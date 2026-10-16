/**
 * UploadArea component supporting drag-and-drop file upload & remote URL conversion.
 */
import { convertApi } from '../api/convert.js';
import { showToast } from './Toast.js';

const { ref } = window.Vue || (await import('https://cdn.jsdelivr.net/npm/vue@3/dist/vue.esm-browser.prod.js'));

const ALLOWED_EXTS = [
  '.pdf', '.docx', '.pptx', '.xlsx', '.xls',
  '.jpg', '.jpeg', '.png', '.mp3', '.wav',
  '.html', '.csv', '.json', '.xml', '.zip', '.epub'
];

export const UploadAreaComponent = {
  name: 'UploadArea',
  props: {
    loading: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['conversion-success', 'classification-only', 'start-loading', 'stop-loading'],
  setup(props, { emit }) {
    const activeTab = ref('file'); // 'file' | 'url'
    const isDragOver = ref(false);
    const selectedFile = ref(null);
    const fileInput = ref(null);
    const uploadProgress = ref(0);

    // Options
    const autoClassify = ref(true);
    const forceOcr = ref(false);
    const customPrompt = ref('');
    const showAdvanced = ref(false);

    // URL input
    const remoteUrl = ref('');

    const formatBytes = (bytes) => {
      if (!bytes || bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
    };

    const validateFile = (file) => {
      if (!file) return false;
      const name = file.name || '';
      const dotIdx = name.lastIndexOf('.');
      if (dotIdx === -1) {
        showToast('上传文件缺少扩展名，请检查', 'error');
        return false;
      }
      const ext = name.slice(dotIdx).toLowerCase();
      if (!ALLOWED_EXTS.includes(ext)) {
        showToast(`不支持的文件扩展名 "${ext}"。允许格式：${ALLOWED_EXTS.join(', ')}`, 'error');
        return false;
      }
      if (file.size > 50 * 1024 * 1024) {
        showToast(`文件体积 (${formatBytes(file.size)}) 超过系统限制的 50MB`, 'error');
        return false;
      }
      return true;
    };

    const onFilePicked = (event) => {
      const files = event.target.files;
      if (files && files[0]) {
        if (validateFile(files[0])) {
          selectedFile.value = files[0];
        }
      }
    };

    const onDrop = (event) => {
      isDragOver.value = false;
      const dt = event.dataTransfer;
      if (dt && dt.files && dt.files[0]) {
        if (validateFile(dt.files[0])) {
          selectedFile.value = dt.files[0];
        }
      }
    };

    const triggerFilePicker = () => {
      if (fileInput.value) {
        fileInput.value.click();
      }
    };

    const clearSelectedFile = (e) => {
      if (e) e.stopPropagation();
      selectedFile.value = null;
      if (fileInput.value) {
        fileInput.value.value = '';
      }
    };

    // Execute Conversion
    const executeConversion = async () => {
      if (activeTab.value === 'file') {
        if (!selectedFile.value) {
          showToast('请先选择或拖拽需要转换的文档', 'warning');
          return;
        }

        emit('start-loading', '正在上传并通过 PyTorch 分类模型与 MarkItDown 引擎处理...');
        uploadProgress.value = 10;

        try {
          const res = await convertApi.uploadAndConvert(
            selectedFile.value,
            {
              autoClassify: autoClassify.value,
              forceOcr: forceOcr.value,
              customPrompt: customPrompt.value || undefined,
            },
            (progress) => {
              uploadProgress.value = Math.min(progress, 90);
            }
          );
          uploadProgress.value = 100;
          showToast(`文档 "${res.record.filename}" 转换成功！耗时 ${res.record.duration_ms}ms`, 'success');
          emit('conversion-success', res);
        } catch (err) {
          showToast(err.message || '文档转换失败，请检查文件格式或后端服务', 'error');
        } finally {
          setTimeout(() => { uploadProgress.value = 0; }, 800);
          emit('stop-loading');
        }
      } else {
        // URL Conversion
        if (!remoteUrl.value.trim()) {
          showToast('请输入有效的文档或网页 URL', 'warning');
          return;
        }

        emit('start-loading', '正在进行 Anti-SSRF 安全探测与远程转换...');
        try {
          const res = await convertApi.convertUrl(remoteUrl.value.trim(), {
            autoClassify: autoClassify.value,
            forceOcr: forceOcr.value,
            customPrompt: customPrompt.value || undefined,
          });
          showToast(`远程文档 "${res.record.filename}" 转换成功！`, 'success');
          emit('conversion-success', res);
        } catch (err) {
          showToast(err.message || '远程 URL 转换失败，可能被 Anti-SSRF 防护阻断或链接无法访问', 'error');
        } finally {
          emit('stop-loading');
        }
      }
    };

    // Execute PyTorch Classification Only
    const executeClassifyOnly = async () => {
      if (!selectedFile.value) {
        showToast('请先选择待分类预判的文件', 'warning');
        return;
      }

      emit('start-loading', '正在调用 PyTorch 深度学习二分类模型进行轻重前置路由预判...');
      try {
        const res = await convertApi.classifyFile(selectedFile.value);
        showToast('PyTorch 二分类预判完成！', 'success');
        emit('classification-only', res);
      } catch (err) {
        showToast(err.message || '分类预判失败，请检查 PyTorch 模块权重', 'error');
      } finally {
        emit('stop-loading');
      }
    };

    return {
      activeTab,
      isDragOver,
      selectedFile,
      fileInput,
      uploadProgress,
      autoClassify,
      forceOcr,
      customPrompt,
      showAdvanced,
      remoteUrl,
      ALLOWED_EXTS,
      formatBytes,
      onFilePicked,
      onDrop,
      triggerFilePicker,
      clearSelectedFile,
      executeConversion,
      executeClassifyOnly,
    };
  },
  template: `
    <div class="card upload-wrapper">
      <div class="tabs">
        <button
          :class="['tab-btn', activeTab === 'file' ? 'active' : '']"
          @click="activeTab = 'file'"
        >
          📂 本地文档上传
        </button>
        <button
          :class="['tab-btn', activeTab === 'url' ? 'active' : '']"
          @click="activeTab = 'url'"
        >
          🌐 远程 URL 转换 (Anti-SSRF)
        </button>
      </div>

      <!-- Tab 1: Local File Dropzone -->
      <div v-if="activeTab === 'file'">
        <input
          ref="fileInput"
          type="file"
          style="display: none;"
          :accept="ALLOWED_EXTS.join(',')"
          @change="onFilePicked"
        />

        <div
          v-if="!selectedFile"
          :class="['dropzone', isDragOver ? 'is-dragover' : '']"
          @click="triggerFilePicker"
          @dragover.prevent="isDragOver = true"
          @dragenter.prevent="isDragOver = true"
          @dragleave.prevent="isDragOver = false"
          @drop.prevent="onDrop"
        >
          <div class="dropzone-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <div class="dropzone-title">拖拽文档至此处，或点击浏览选择文件</div>
          <div class="dropzone-desc">支持格式包含各类 PDF、Office 办公文档、图片、网页与压缩包（单个文件最大 50MB）</div>

          <div class="format-tags">
            <span v-for="ext in ALLOWED_EXTS" :key="ext" class="format-tag">{{ ext.toUpperCase() }}</span>
          </div>
        </div>

        <!-- Selected File Banner -->
        <div v-else class="selected-file-banner">
          <div class="file-info">
            <div class="file-icon-badge">
              {{ selectedFile.name.split('.').pop().toUpperCase() }}
            </div>
            <div>
              <div class="file-meta-name" :title="selectedFile.name">{{ selectedFile.name }}</div>
              <div class="file-meta-size">{{ formatBytes(selectedFile.size) }}</div>
            </div>
          </div>

          <div style="display: flex; align-items: center; gap: 8px;">
            <button class="btn btn-secondary btn-sm" @click="triggerFilePicker">更换文件</button>
            <button class="btn btn-subtle btn-sm" @click="clearSelectedFile" title="移除当前文件">✕</button>
          </div>
        </div>
      </div>

      <!-- Tab 2: Remote URL Conversion -->
      <div v-else class="url-input-container">
        <label class="form-label">输入远程文档或网页 URL：</label>
        <div class="input-with-button">
          <input
            v-model="remoteUrl"
            type="url"
            class="input-field"
            placeholder="https://example.com/sample_invoice.pdf"
            @keyup.enter="executeConversion"
          />
        </div>
        <div class="ssrf-notice">
          <span>🛡️</span>
          <span>已启用后端 Strict Anti-SSRF 防护白名单，自动屏蔽内网私有 IP (10.x, 192.168.x, 172.16.x) 与本地回环</span>
        </div>
      </div>

      <!-- Upload Progress Bar -->
      <div v-if="uploadProgress > 0" class="progress-container">
        <div class="progress-bar" :style="{ width: uploadProgress + '%' }"></div>
      </div>

      <!-- Conversion Options & Action Buttons -->
      <div class="options-bar">
        <div class="toggles-group">
          <label class="toggle-item" title="利用训练好的 PyTorch 深度学习轻量网络实时二分类预判，自动路由至轻量本地解析或重型视觉 OCR">
            <input type="checkbox" v-model="autoClassify" />
            <span>智能自动路由</span>
            <span class="badge-dl">PyTorch DL</span>
          </label>

          <label class="toggle-item" title="跳过二分类预判，强制使用视觉多模态大模型进行排版还原">
            <input type="checkbox" v-model="forceOcr" />
            <span>强制视觉 OCR</span>
          </label>

          <button
            class="btn btn-subtle btn-sm"
            style="font-size: 11px; padding: 2px 6px;"
            @click="showAdvanced = !showAdvanced"
          >
            {{ showAdvanced ? '收起高级设置' : '高级 OCR 提示词' }}
          </button>
        </div>

        <div class="actions-group">
          <button
            v-if="activeTab === 'file' && selectedFile"
            class="btn btn-secondary"
            :disabled="loading"
            @click="executeClassifyOnly"
            title="只运行 PyTorch 深度学习二分类推理，查看置信度与路由策略"
          >
            🔍 仅执行分类预判
          </button>

          <button
            class="btn btn-primary"
            :disabled="loading || (activeTab === 'file' && !selectedFile)"
            @click="executeConversion"
          >
            <span v-if="loading">正在处理中...</span>
            <span v-else>🚀 开始智能转换</span>
          </button>
        </div>
      </div>

      <!-- Advanced Custom Prompt Input (Optional) -->
      <div v-if="showAdvanced" style="margin-top: 14px; padding-top: 14px; border-top: 1px dashed #e2e8f0;">
        <label class="form-label" style="font-size: 12px;">自定义 OCR 视觉提取提示词 (LLM Vision Prompt):</label>
        <input
          v-model="customPrompt"
          type="text"
          class="form-input"
          style="font-size: 13px;"
          placeholder="例如：提取全部表格并转换为标准 Markdown Table，保留原图中的数学公式与批注"
        />
      </div>
    </div>
  `,
};
