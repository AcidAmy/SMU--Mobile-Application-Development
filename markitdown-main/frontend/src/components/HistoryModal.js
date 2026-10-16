/**
 * Conversion History Modal / Drawer component (Section 5.4).
 * Lists previous document conversions with PyTorch classification metadata,
 * detail preview loading, and record deletion.
 */
import { recordsApi } from '../api/records.js';
import { showToast } from './Toast.js';

const { ref, computed, onMounted } =
  window.Vue || (await import('https://cdn.jsdelivr.net/npm/vue@3/dist/vue.esm-browser.prod.js'));

export const HistoryModalComponent = {
  name: 'HistoryModal',
  props: {
    user: {
      type: Object,
      default: null,
    },
  },
  emits: ['close', 'load-record', 'update-count'],
  setup(props, { emit }) {
    const loading = ref(false);
    const records = ref([]);
    const totalCount = ref(0);
    const searchQuery = ref('');

    const fetchRecords = async () => {
      loading.value = true;
      try {
        const res = await recordsApi.getRecords(0, 100);
        records.value = res.items || [];
        totalCount.value = res.total || 0;
        emit('update-count', totalCount.value);
      } catch (err) {
        showToast(err.message || '获取历史转换记录失败', 'error');
      } finally {
        loading.value = false;
      }
    };

    onMounted(() => {
      fetchRecords();
    });

    const filteredRecords = computed(() => {
      const q = searchQuery.value.trim().toLowerCase();
      if (!q) return records.value;
      return records.value.filter((r) =>
        (r.filename || '').toLowerCase().includes(q) ||
        (r.title || '').toLowerCase().includes(q) ||
        (r.file_type || '').toLowerCase().includes(q)
      );
    });

    const formatBytes = (bytes) => {
      if (!bytes || bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
    };

    const formatDate = (dateStr) => {
      if (!dateStr) return '';
      try {
        const d = new Date(dateStr);
        return d.toLocaleString('zh-CN', {
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        });
      } catch {
        return dateStr;
      }
    };

    // Load Record Detail into Viewer
    const loadRecordDetail = async (record) => {
      loading.value = true;
      try {
        const detail = await recordsApi.getRecordDetail(record.id);
        emit('load-record', detail);
        showToast(`已加载记录 "${record.filename}"`, 'info');
        emit('close');
      } catch (err) {
        showToast(err.message || '加载详情记录失败', 'error');
      } finally {
        loading.value = false;
      }
    };

    // Delete Record
    const deleteRecord = async (record, event) => {
      event.stopPropagation();
      if (!props.user) {
        showToast('访客模式无法直接删除全局记录，请登录您的账号', 'warning');
        return;
      }
      if (!confirm(`确定要删除转换记录 "${record.filename}" 吗？`)) {
        return;
      }

      try {
        await recordsApi.deleteRecord(record.id);
        showToast('记录已成功删除', 'success');
        records.value = records.value.filter((r) => r.id !== record.id);
        totalCount.value = Math.max(0, totalCount.value - 1);
        emit('update-count', totalCount.value);
      } catch (err) {
        showToast(err.message || '删除失败，可能无权限删除此记录', 'error');
      }
    };

    return {
      loading,
      records,
      totalCount,
      searchQuery,
      filteredRecords,
      fetchRecords,
      formatBytes,
      formatDate,
      loadRecordDetail,
      deleteRecord,
    };
  },
  template: `
    <div class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-card modal-lg">
        <div class="modal-header">
          <div style="display: flex; align-items: center; gap: 8px;">
            <div class="modal-title">📜 文档转换历史记录</div>
            <span style="font-size: 12px; background: #e2e8f0; color: #475569; padding: 2px 8px; border-radius: 999px; font-weight: 600;">
              共 {{ totalCount }} 条
            </span>
          </div>

          <div style="display: flex; align-items: center; gap: 10px;">
            <button class="btn btn-secondary btn-sm" @click="fetchRecords" :disabled="loading" title="刷新列表">
              🔄 刷新
            </button>
            <button class="modal-close" @click="$emit('close')" title="关闭">&times;</button>
          </div>
        </div>

        <div class="modal-body">
          <!-- Search & Filter bar -->
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; gap: 12px;">
            <input
              v-model="searchQuery"
              type="text"
              class="form-input"
              style="max-width: 340px; font-size: 13px; padding: 8px 12px;"
              placeholder="搜索文件名、类型..."
            />

            <div v-if="!user" style="font-size: 12px; color: #64748b;">
              💡 提示：<a href="#" style="color: #2563eb; text-decoration: none;" @click.prevent="$emit('close'); $emit('open-auth')">登录账号</a> 可持久化管理个人历史并支持删除
            </div>
          </div>

          <!-- Records Table -->
          <div class="records-table-container">
            <table class="records-table">
              <thead>
                <tr>
                  <th>文档名称</th>
                  <th>类型/大小</th>
                  <th>PyTorch 分类结果</th>
                  <th>处理策略</th>
                  <th>耗时</th>
                  <th>转换时间</th>
                  <th style="text-align: right;">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in filteredRecords" :key="r.id">
                  <td>
                    <div class="record-filename" :title="r.filename">
                      {{ r.filename }}
                    </div>
                    <div v-if="r.title && r.title !== r.filename" style="font-size: 11px; color: #94a3b8; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                      {{ r.title }}
                    </div>
                  </td>

                  <td>
                    <span style="font-weight: 600; text-transform: uppercase; font-size: 11px; background: #f1f5f9; padding: 1px 5px; border-radius: 3px;">
                      {{ r.file_type || 'file' }}
                    </span>
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                      {{ formatBytes(r.file_size) }}
                    </div>
                  </td>

                  <td>
                    <div v-if="r.classifier_class === 'standard' || r.classifier_label === 0">
                      <span class="badge-status success" title="常规电子文档">
                        📄 常规文档
                      </span>
                      <span v-if="r.classifier_confidence" style="font-size: 11px; color: #166534; margin-left: 4px;">
                        {{ (r.classifier_confidence * 100).toFixed(0) }}%
                      </span>
                    </div>
                    <div v-else-if="r.classifier_class === 'scanned_or_complex' || r.classifier_label === 1">
                      <span class="badge-status failed" style="background: #fef3c7; color: #92400e;" title="扫描件/复杂图表">
                        📷 扫描件/图表
                      </span>
                      <span v-if="r.classifier_confidence" style="font-size: 11px; color: #92400e; margin-left: 4px;">
                        {{ (r.classifier_confidence * 100).toFixed(0) }}%
                      </span>
                    </div>
                    <div v-else style="font-size: 11px; color: #94a3b8;">
                      未触发分类
                    </div>
                  </td>

                  <td>
                    <span v-if="r.converted_with_ocr" style="font-size: 11px; color: #92400e; font-weight: 600;">
                      OCR 增强
                    </span>
                    <span v-else style="font-size: 11px; color: #15803d; font-weight: 600;">
                      原生解析
                    </span>
                  </td>

                  <td style="font-family: var(--font-mono); font-size: 12px; color: #475569;">
                    {{ r.duration_ms ? r.duration_ms + 'ms' : '-' }}
                  </td>

                  <td style="font-size: 12px; color: #64748b; white-space: nowrap;">
                    {{ formatDate(r.created_at) }}
                  </td>

                  <td style="text-align: right; white-space: nowrap;">
                    <button
                      class="btn btn-secondary btn-sm"
                      style="padding: 3px 8px; font-size: 11px;"
                      @click="loadRecordDetail(r)"
                      title="在双栏对比器中载入该记录的 Markdown 内容"
                    >
                      查看预览
                    </button>
                    <button
                      v-if="user"
                      class="btn btn-danger btn-sm"
                      style="padding: 3px 8px; font-size: 11px; margin-left: 6px;"
                      @click="deleteRecord(r, $event)"
                      title="删除此记录"
                    >
                      删除
                    </button>
                  </td>
                </tr>

                <tr v-if="filteredRecords.length === 0">
                  <td colspan="7" style="text-align: center; padding: 40px; color: #94a3b8;">
                    <div style="font-size: 28px; margin-bottom: 8px;">📭</div>
                    <div>暂无转换历史记录</div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  `,
};
