/**
 * Markdown Dual-Pane Split Viewer (Section 5.4).
 * Provides side-by-side comparison between raw Markdown source code and rendered HTML preview,
 * featuring synchronized scrolling, clipboard copy, and file download.
 */
import { showToast } from './Toast.js';

const { ref, computed, watch, nextTick, onMounted } =
  window.Vue || (await import('https://cdn.jsdelivr.net/npm/vue@3/dist/vue.esm-browser.prod.js'));

export const MarkdownViewerComponent = {
  name: 'MarkdownViewer',
  props: {
    markdown: {
      type: String,
      default: '',
    },
    title: {
      type: String,
      default: '',
    },
    durationMs: {
      type: Number,
      default: null,
    },
    convertedWithOcr: {
      type: Boolean,
      default: false,
    },
    filename: {
      type: String,
      default: 'document',
    },
  },
  setup(props) {
    const viewMode = ref('split'); // 'split' | 'source' | 'preview'
    const syncScroll = ref(true);
    const isFullscreen = ref(false);
    const copied = ref(false);

    const sourcePane = ref(null);
    const previewPane = ref(null);
    let isScrolling = false;

    // Word and line statistics
    const stats = computed(() => {
      const text = props.markdown || '';
      const chars = text.length;
      const lines = text ? text.split('\n').length : 0;
      const words = text ? (text.match(/\S+/g) || []).length : 0;
      return { chars, lines, words };
    });

    // Rendered HTML from Markdown using window.marked or fallback
    const renderedHtml = computed(() => {
      if (!props.markdown) return '';
      try {
        if (window.marked && typeof window.marked.parse === 'function') {
          return window.marked.parse(props.markdown, {
            gfm: true,
            breaks: true,
          });
        }
      } catch (e) {
        console.error('Marked parse error:', e);
      }

      // Safe lightweight fallback if marked is not yet loaded
      return props.markdown
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n\n/g, '<br/><br/>')
        .replace(/\n/g, '<br/>');
    });

    // Highlight code blocks whenever rendered HTML updates
    const applySyntaxHighlighting = () => {
      nextTick(() => {
        if (window.hljs && previewPane.value) {
          const codeBlocks = previewPane.value.querySelectorAll('pre code');
          codeBlocks.forEach((block) => {
            window.hljs.highlightElement(block);
          });
        }
      });
    };

    watch(() => props.markdown, () => {
      applySyntaxHighlighting();
    });

    onMounted(() => {
      applySyntaxHighlighting();
    });

    // Synchronized scrolling handlers
    const handleSourceScroll = () => {
      if (!syncScroll.value || isScrolling || !sourcePane.value || !previewPane.value) return;
      isScrolling = true;

      const src = sourcePane.value;
      const prev = previewPane.value;
      const scrollPercentage = src.scrollTop / (src.scrollHeight - src.clientHeight || 1);
      prev.scrollTop = scrollPercentage * (prev.scrollHeight - prev.clientHeight);

      setTimeout(() => { isScrolling = false; }, 50);
    };

    const handlePreviewScroll = () => {
      if (!syncScroll.value || isScrolling || !sourcePane.value || !previewPane.value) return;
      isScrolling = true;

      const src = sourcePane.value;
      const prev = previewPane.value;
      const scrollPercentage = prev.scrollTop / (prev.scrollHeight - prev.clientHeight || 1);
      src.scrollTop = scrollPercentage * (src.scrollHeight - src.clientHeight);

      setTimeout(() => { isScrolling = false; }, 50);
    };

    // Copy Markdown to Clipboard
    const copyToClipboard = async () => {
      if (!props.markdown) return;
      try {
        await navigator.clipboard.writeText(props.markdown);
        copied.value = true;
        showToast('Markdown 源码已成功复制到剪贴板！', 'success');
        setTimeout(() => { copied.value = false; }, 2000);
      } catch {
        // Fallback for non-https contexts
        const textarea = document.createElement('textarea');
        textarea.value = props.markdown;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        copied.value = true;
        showToast('Markdown 源码已成功复制！', 'success');
        setTimeout(() => { copied.value = false; }, 2000);
      }
    };

    // Download Markdown File
    const downloadMarkdown = () => {
      if (!props.markdown) return;
      const blob = new Blob([props.markdown], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const baseName = props.filename.replace(/\.[^/.]+$/, '') || 'document';
      a.href = url;
      a.download = `${baseName}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast(`已下载文件 "${baseName}.md"`, 'success');
    };

    const toggleFullscreen = () => {
      isFullscreen.value = !isFullscreen.value;
    };

    return {
      viewMode,
      syncScroll,
      isFullscreen,
      copied,
      sourcePane,
      previewPane,
      stats,
      renderedHtml,
      handleSourceScroll,
      handlePreviewScroll,
      copyToClipboard,
      downloadMarkdown,
      toggleFullscreen,
    };
  },
  template: `
    <div :class="['viewer-container', isFullscreen ? 'fullscreen' : '']">
      <!-- Toolbar -->
      <div class="viewer-toolbar">
        <div class="viewer-title-group">
          <span style="font-size: 16px;">📝</span>
          <div class="viewer-doc-title" :title="title || filename">
            {{ title || filename || 'Markdown 对比预览' }}
          </div>
          <span v-if="durationMs !== null" class="timing-badge">
            ⏱️ {{ durationMs }}ms
          </span>
          <span v-if="convertedWithOcr" class="ocr-badge">
            📷 OCR 增强转换
          </span>
          <span v-else class="timing-badge" style="background: #dcfce7; color: #166534;">
            ⚡ 原生零开销解析
          </span>
        </div>

        <div class="viewer-controls">
          <!-- View Switcher -->
          <div class="view-mode-toggle">
            <button
              :class="['mode-btn', viewMode === 'split' ? 'active' : '']"
              @click="viewMode = 'split'"
              title="双栏左右对比"
            >
              双栏对比
            </button>
            <button
              :class="['mode-btn', viewMode === 'source' ? 'active' : '']"
              @click="viewMode = 'source'"
              title="仅展示 Markdown 纯文本源码"
            >
              源码
            </button>
            <button
              :class="['mode-btn', viewMode === 'preview' ? 'active' : '']"
              @click="viewMode = 'preview'"
              title="仅展示富文本排版预览"
            >
              预览
            </button>
          </div>

          <!-- Sync Scroll Switch -->
          <label
            v-if="viewMode === 'split'"
            style="display: flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 500; color: #64748b; cursor: pointer; user-select: none;"
            title="开启/关闭两栏同步联动滚动"
          >
            <input type="checkbox" v-model="syncScroll" style="accent-color: #2563eb;" />
            <span>同步滚动</span>
          </label>

          <!-- Copy Button -->
          <button class="btn btn-secondary btn-sm" @click="copyToClipboard" title="复制 Markdown 源码">
            <span>{{ copied ? '✅ 已复制' : '📋 复制源码' }}</span>
          </button>

          <!-- Download Button -->
          <button class="btn btn-secondary btn-sm" @click="downloadMarkdown" title="导出下载为 .md 文件">
            <span>💾 下载 .md</span>
          </button>

          <!-- Fullscreen Button -->
          <button class="btn btn-subtle btn-sm" @click="toggleFullscreen" title="切换全屏专注模式">
            <span v-if="isFullscreen">🗗 退出全屏</span>
            <span v-else>⛶ 全屏</span>
          </button>
        </div>
      </div>

      <!-- Dual Pane Container -->
      <div
        v-if="markdown"
        :class="[
          'dual-pane',
          viewMode === 'source' ? 'source-only' : '',
          viewMode === 'preview' ? 'preview-only' : ''
        ]"
      >
        <!-- Left: Source Code Pane -->
        <div
          ref="sourcePane"
          class="pane source-pane"
          @scroll="handleSourceScroll"
        >
          <div class="source-toolbar-floating">
            <span style="font-size: 11px; color: #94a3b8; background: #fff; padding: 2px 8px; border-radius: 4px; border: 1px solid #e2e8f0;">
              {{ stats.lines }} 行 · {{ stats.words }} 词 · {{ stats.chars }} 字符
            </span>
          </div>
          <code>{{ markdown }}</code>
        </div>

        <!-- Right: Rendered HTML Preview Pane -->
        <div
          ref="previewPane"
          class="pane preview-pane"
          @scroll="handlePreviewScroll"
        >
          <div class="markdown-preview" v-html="renderedHtml"></div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="empty-viewer">
        <div class="empty-icon">📄</div>
        <div style="font-size: 16px; font-weight: 600; color: #475569; margin-bottom: 6px;">
          暂无已渲染的 Markdown 内容
        </div>
        <div style="font-size: 13px; max-width: 440px;">
          请在上方拖拽或选择一份文档（如 PDF、Word、Excel、图片等），并点击“开始智能转换”，系统将在此呈现双栏对比。
        </div>
      </div>
    </div>
  `,
};
