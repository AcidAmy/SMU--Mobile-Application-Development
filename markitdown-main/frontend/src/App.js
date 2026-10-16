/**
 * Main Application Component for MarkItDown Frontend (Section 5.4).
 */
import { authApi } from './api/auth.js';
import { systemApi } from './api/system.js';
import { recordsApi } from './api/records.js';
import { showToast, ToastComponent } from './components/Toast.js';
import { NavbarComponent } from './components/Navbar.js';
import { AuthModalComponent } from './components/AuthModal.js';
import { UploadAreaComponent } from './components/UploadArea.js';
import { ClassifierCardComponent } from './components/ClassifierCard.js';
import { MarkdownViewerComponent } from './components/MarkdownViewer.js';
import { HistoryModalComponent } from './components/HistoryModal.js';
import { HealthModalComponent } from './components/HealthModal.js';

const { ref, onMounted } =
  window.Vue || (await import('https://cdn.jsdelivr.net/npm/vue@3/dist/vue.esm-browser.prod.js'));

export const AppComponent = {
  name: 'App',
  components: {
    Navbar: NavbarComponent,
    AuthModal: AuthModalComponent,
    UploadArea: UploadAreaComponent,
    ClassifierCard: ClassifierCardComponent,
    MarkdownViewer: MarkdownViewerComponent,
    HistoryModal: HistoryModalComponent,
    HealthModal: HealthModalComponent,
    ToastContainer: ToastComponent,
  },
  setup() {
    const user = ref(authApi.getCachedUser());
    const showAuthModal = ref(false);
    const showHistoryModal = ref(false);
    const showHealthModal = ref(false);

    // Backend health state
    const backendOnline = ref(false);
    const backendHealth = ref(null);
    const historyCount = ref(0);

    // Global loading state
    const loading = ref(false);
    const loadingMessage = ref('');

    // Conversion and Classification State
    const currentClassification = ref(null);
    const currentMarkdown = ref('');
    const currentTitle = ref('');
    const currentFilename = ref('');
    const currentDurationMs = ref(null);
    const currentWithOcr = ref(false);

    // Check backend health
    const checkHealth = async () => {
      try {
        const res = await systemApi.getHealth();
        backendHealth.value = res;
        backendOnline.value = true;
      } catch {
        backendOnline.value = false;
        backendHealth.value = null;
      }
    };

    // Update history count
    const updateHistoryCount = async () => {
      try {
        const res = await recordsApi.getRecords(0, 1);
        historyCount.value = res.total || 0;
      } catch {
        // Ignore if backend offline
      }
    };

    // Check user token validity
    const checkAuth = async () => {
      if (authApi.hasToken()) {
        try {
          const profile = await authApi.getProfile();
          user.value = profile;
        } catch {
          user.value = null;
        }
      }
    };

    onMounted(async () => {
      await checkHealth();
      await checkAuth();
      await updateHistoryCount();

      // Listen for token expiration event from Axios interceptor
      window.addEventListener('auth:expired', (e) => {
        user.value = null;
        if (e.detail?.hadToken) {
          showToast('登录状态已失效，已切换至访客模式', 'warning');
        }
      });
    });

    const handleStartLoading = (msg) => {
      loading.value = true;
      loadingMessage.value = msg || '处理中...';
    };

    const handleStopLoading = () => {
      loading.value = false;
      loadingMessage.value = '';
    };

    // Called when a file/url conversion completes successfully
    const handleConversionSuccess = (res) => {
      if (!res) return;
      currentMarkdown.value = res.markdown || '';
      currentTitle.value = res.title || res.record?.title || '';
      currentFilename.value = res.record?.filename || '';
      currentDurationMs.value = res.record?.duration_ms || null;
      currentWithOcr.value = !!res.record?.converted_with_ocr;

      // Extract classification from either top-level classification or record
      if (res.classification) {
        currentClassification.value = res.classification;
      } else if (res.record && res.record.classifier_class) {
        currentClassification.value = {
          file_name: res.record.filename,
          label: res.record.classifier_label,
          class_name: res.record.classifier_class,
          confidence: res.record.classifier_confidence || 0.99,
          requires_ocr: res.record.requires_ocr,
          probabilities: {
            [res.record.classifier_class]: res.record.classifier_confidence || 0.99,
          },
        };
      }

      // Refresh records counter
      updateHistoryCount();
    };

    // Called when user clicks "仅执行分类预判"
    const handleClassificationOnly = (res) => {
      currentClassification.value = res;
    };

    // Called when user loads a record from history drawer
    const handleLoadRecord = (recordDetail) => {
      if (!recordDetail) return;
      currentMarkdown.value = recordDetail.markdown_content || '';
      currentTitle.value = recordDetail.title || recordDetail.filename || '';
      currentFilename.value = recordDetail.filename || '';
      currentDurationMs.value = recordDetail.duration_ms || null;
      currentWithOcr.value = !!recordDetail.converted_with_ocr;

      if (recordDetail.classifier_class) {
        currentClassification.value = {
          file_name: recordDetail.filename,
          label: recordDetail.classifier_label,
          class_name: recordDetail.classifier_class,
          confidence: recordDetail.classifier_confidence || 0.95,
          requires_ocr: recordDetail.requires_ocr,
          probabilities: {
            [recordDetail.classifier_class]: recordDetail.classifier_confidence || 0.95,
          },
        };
      }
    };

    const handleLogout = () => {
      authApi.logout();
      user.value = null;
      showToast('已安全退出登录', 'info');
      updateHistoryCount();
    };

    const handleAuthSuccess = (loggedUser) => {
      user.value = loggedUser;
      updateHistoryCount();
    };

    return {
      user,
      showAuthModal,
      showHistoryModal,
      showHealthModal,
      backendOnline,
      backendHealth,
      historyCount,
      loading,
      loadingMessage,
      currentClassification,
      currentMarkdown,
      currentTitle,
      currentFilename,
      currentDurationMs,
      currentWithOcr,
      checkHealth,
      handleStartLoading,
      handleStopLoading,
      handleConversionSuccess,
      handleClassificationOnly,
      handleLoadRecord,
      handleLogout,
      handleAuthSuccess,
    };
  },
  template: `
    <div class="app-container">
      <!-- Navbar -->
      <Navbar
        :user="user"
        :backend-online="backendOnline"
        :backend-health="backendHealth"
        :history-count="historyCount"
        @open-auth="showAuthModal = true"
        @open-history="showHistoryModal = true"
        @open-health-config="showHealthModal = true"
        @logout="handleLogout"
      />

      <!-- Main Layout -->
      <main class="main-content">
        <!-- Hero Tagline -->
        <div style="margin-bottom: 24px; text-align: left;">
          <h1 style="font-size: 24px; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">
            文档智能转 Markdown 工作台
          </h1>
          <p style="font-size: 14px; color: #64748b; margin-top: 4px;">
            基于 PyTorch 轻量二分类网络前置动态路由 · 支持原生高速提取与 OCR 视觉大模型增强排版
          </p>
        </div>

        <!-- Section 1: Upload & Input Area -->
        <UploadArea
          :loading="loading"
          @start-loading="handleStartLoading"
          @stop-loading="handleStopLoading"
          @conversion-success="handleConversionSuccess"
          @classification-only="handleClassificationOnly"
        />

        <!-- Section 2: PyTorch Deep Learning Classifier Prediction Card -->
        <ClassifierCard
          v-if="currentClassification"
          :result="currentClassification"
          @dismiss="currentClassification = null"
        />

        <!-- Section 3: Dual-Pane Markdown Viewer & Comparison -->
        <MarkdownViewer
          :markdown="currentMarkdown"
          :title="currentTitle"
          :filename="currentFilename"
          :duration-ms="currentDurationMs"
          :converted-with-ocr="currentWithOcr"
        />
      </main>

      <!-- Footer -->
      <footer class="app-footer">
        <div class="footer-inner">
          <div>
            <strong>MarkItDown Full-Stack Platform</strong> &copy; 2026 · Section 5.4 Implementation
          </div>
          <div style="display: flex; gap: 16px; color: #64748b;">
            <span>PyTorch 深度学习二分类</span>
            <span>FastAPI 后端</span>
            <span>Vue3 + Axios 前端</span>
            <span>Strict Anti-SSRF</span>
          </div>
        </div>
      </footer>

      <!-- Modals -->
      <AuthModal
        v-if="showAuthModal"
        @close="showAuthModal = false"
        @auth-success="handleAuthSuccess"
      />

      <HistoryModal
        v-if="showHistoryModal"
        :user="user"
        @close="showHistoryModal = false"
        @open-auth="showAuthModal = true"
        @load-record="handleLoadRecord"
        @update-count="historyCount = $event"
      />

      <HealthModal
        v-if="showHealthModal"
        :health="backendHealth"
        :online="backendOnline"
        @close="showHealthModal = false"
        @refresh-health="checkHealth"
      />

      <!-- Global Toast Container -->
      <ToastContainer />
    </div>
  `,
};
