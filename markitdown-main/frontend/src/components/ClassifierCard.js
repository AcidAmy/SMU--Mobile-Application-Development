/**
 * PyTorch Document Classifier Prediction Result Card (Section 5.1 & 5.4).
 * Highlights classification into '常规电子文档' vs '扫描件/复杂图表' with confidence and routing decision.
 */
const { computed } = window.Vue || (await import('https://cdn.jsdelivr.net/npm/vue@3/dist/vue.esm-browser.prod.js'));

export const ClassifierCardComponent = {
  name: 'ClassifierCard',
  props: {
    result: {
      type: Object,
      required: true,
    },
  },
  emits: ['dismiss'],
  setup(props) {
    const isStandard = computed(() => {
      if (!props.result) return true;
      return props.result.label === 0 || props.result.class_name === 'standard';
    });

    const confidencePercent = computed(() => {
      if (!props.result || props.result.confidence === undefined) return '0.0%';
      return (props.result.confidence * 100).toFixed(1) + '%';
    });

    const standardProbPercent = computed(() => {
      const p = props.result?.probabilities?.standard;
      if (p !== undefined) return (p * 100).toFixed(1) + '%';
      return isStandard.value ? confidencePercent.value : '0.0%';
    });

    const scannedProbPercent = computed(() => {
      const p = props.result?.probabilities?.scanned_or_complex;
      if (p !== undefined) return (p * 100).toFixed(1) + '%';
      return !isStandard.value ? confidencePercent.value : '0.0%';
    });

    const meterStandardWidth = computed(() => {
      const p = props.result?.probabilities?.standard;
      if (p !== undefined) return (p * 100) + '%';
      return isStandard.value ? (props.result?.confidence * 100) + '%' : '0%';
    });

    const meterScannedWidth = computed(() => {
      const p = props.result?.probabilities?.scanned_or_complex;
      if (p !== undefined) return (p * 100) + '%';
      return !isStandard.value ? (props.result?.confidence * 100) + '%' : '0%';
    });

    return {
      isStandard,
      confidencePercent,
      standardProbPercent,
      scannedProbPercent,
      meterStandardWidth,
      meterScannedWidth,
    };
  },
  template: `
    <div :class="['classifier-card', isStandard ? 'standard' : 'scanned']">
      <div class="classifier-header">
        <div class="classifier-title-wrap">
          <div class="classifier-icon-box">
            <span v-if="isStandard">📄</span>
            <span v-else>📷</span>
          </div>
          <div>
            <div class="classifier-label-name">
              PyTorch 识别结果：
              <span v-if="isStandard" style="text-decoration: underline;">常规电子文档 (Standard)</span>
              <span v-else style="text-decoration: underline;">扫描件 / 复杂图表 (Scanned & Complex)</span>
            </div>
            <div class="classifier-tagline">
              <span v-if="isStandard">
                该文档排版规范、含原生电子文本流，已自动命中本地高速转换通道，零 API 成本毫秒级生成。
              </span>
              <span v-else>
                该文档具有图像影印、扫描噪点或多栏复杂表格特征，系统推荐/触发视觉多模态大模型 OCR 增强。
              </span>
            </div>
          </div>
        </div>

        <div style="display: flex; align-items: flex-start; gap: 16px;">
          <div class="confidence-display">
            <div class="confidence-value">{{ confidencePercent }}</div>
            <div class="confidence-label">模型预测置信度</div>
          </div>
          <button
            class="btn btn-subtle btn-sm"
            style="padding: 2px 6px; font-size: 14px; color: #94a3b8;"
            @click="$emit('dismiss')"
            title="关闭该预测卡片"
          >
            ✕
          </button>
        </div>
      </div>

      <!-- Visual Confidence Distribution Meter -->
      <div class="confidence-meter" title="概率分布对比：绿色为常规电子文档，橙色为扫描件/复杂文档">
        <div class="meter-fill-standard" :style="{ width: meterStandardWidth }"></div>
        <div class="meter-fill-scanned" :style="{ width: meterScannedWidth }"></div>
      </div>

      <!-- Footer & Metadata -->
      <div class="classifier-footer">
        <div class="routing-rule">
          <span>⚙️ 调度决策：</span>
          <span v-if="isStandard">调用原生解析器 (MarkItDown Native Fast-Path)</span>
          <span v-else>调用 OCR 插件 (MarkItDown-OCR Plugin with Vision LLM)</span>
        </div>

        <div class="probs-breakdown">
          <span class="prob-badge" title="常规文档预测概率">
            常规电子文档: <strong>{{ standardProbPercent }}</strong>
          </span>
          <span class="prob-badge" title="扫描/复杂图表预测概率">
            扫描件/复杂图表: <strong>{{ scannedProbPercent }}</strong>
          </span>
          <span
            v-if="result.model_type"
            class="prob-badge"
            style="background: #e0e7ff; color: #3730a3; border-color: #c7d2fe;"
          >
            网络架构: {{ result.model_type.toUpperCase() }}
          </span>
        </div>
      </div>
    </div>
  `,
};
