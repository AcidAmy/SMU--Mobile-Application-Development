/**
 * Backend Diagnostics & Settings Modal.
 */
import { config } from '../config.js';
import { systemApi } from '../api/system.js';
import { showToast } from './Toast.js';

const { ref } = window.Vue || (await import('https://cdn.jsdelivr.net/npm/vue@3/dist/vue.esm-browser.prod.js'));

export const HealthModalComponent = {
  name: 'HealthModal',
  props: {
    health: {
      type: Object,
      default: null,
    },
    online: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['close', 'refresh-health'],
  setup(props, { emit }) {
    const apiUrlInput = ref(config.API_BASE_URL);

    const saveApiUrl = () => {
      if (!apiUrlInput.value.trim()) return;
      config.setApiBaseUrl(apiUrlInput.value.trim());
      showToast('API 地址已更新，正在重新连接...', 'info');
      emit('refresh-health');
      emit('close');
    };

    const resetApiUrl = () => {
      config.resetApiBaseUrl();
      apiUrlInput.value = config.API_BASE_URL;
      showToast('已恢复默认 API 地址', 'info');
      emit('refresh-health');
    };

    return {
      apiUrlInput,
      saveApiUrl,
      resetApiUrl,
    };
  },
  template: `
    <div class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-card">
        <div class="modal-header">
          <div class="modal-title">⚙️ 后端服务连接与诊断</div>
          <button class="modal-close" @click="$emit('close')" title="关闭">&times;</button>
        </div>

        <div class="modal-body">
          <!-- Status Banner -->
          <div
            :style="{
              background: online ? '#ecfdf5' : '#fef2f2',
              border: '1px solid ' + (online ? '#a7f3d0' : '#fecaca'),
              color: online ? '#065f46' : '#991b1b',
              padding: '12px 16px',
              borderRadius: '8px',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              fontSize: '13px'
            }"
          >
            <span style="font-size: 18px;">{{ online ? '🟢' : '🔴' }}</span>
            <div>
              <div style="font-weight: 700;">
                {{ online ? 'FastAPI 后端服务连接正常' : '无法连接到 FastAPI 后端服务' }}
              </div>
              <div style="font-size: 11px; opacity: 0.9; margin-top: 2px;">
                {{ online ? '已就绪并可接收文档转换请求' : '请确认已启动 uvicorn backend.main:app --port 8000' }}
              </div>
            </div>
          </div>

          <!-- Diagnostic details if online -->
          <div v-if="health" style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; margin-bottom: 16px; font-size: 12px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
              <span style="color: #64748b;">后端版本:</span>
              <strong style="font-family: var(--font-mono);">v{{ health.version }}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
              <span style="color: #64748b;">PyTorch 文档分类器:</span>
              <strong :style="{ color: health.classifier_loaded ? '#16a34a' : '#dc2626' }">
                {{ health.classifier_loaded ? '✅ 已加载 (Ready)' : '❌ 未就绪' }}
              </strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
              <span style="color: #64748b;">markitdown-ocr 插件:</span>
              <strong>{{ health.ocr_plugin_available ? '✅ 可用' : '⚠️ 未安装/内置回退' }}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
              <span style="color: #64748b;">OpenAI 外部视觉 API:</span>
              <strong>{{ health.openai_configured ? '✅ 已配置密钥' : '⚠️ 未配置 (可使用本地模式)' }}</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span style="color: #64748b;">单文件上限:</span>
              <strong>{{ health.max_file_size_mb }} MB</strong>
            </div>
          </div>

          <!-- API Base URL Customizer -->
          <div class="form-group">
            <label class="form-label">FastAPI 后端 API 接口地址：</label>
            <input
              v-model="apiUrlInput"
              type="text"
              class="form-input"
              placeholder="http://127.0.0.1:8000/api"
            />
            <div class="form-helper">
              若在其他端口（如 8080/8001）运行后端，请在此修改
            </div>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px;">
            <button class="btn btn-secondary btn-sm" @click="resetApiUrl">恢复默认</button>
            <button class="btn btn-primary btn-sm" @click="saveApiUrl">保存并测试连接</button>
          </div>
        </div>
      </div>
    </div>
  `,
};
