/**
 * Navbar component for MarkItDown.
 */
export const NavbarComponent = {
  name: 'Navbar',
  props: {
    user: {
      type: Object,
      default: null,
    },
    backendHealth: {
      type: Object,
      default: null,
    },
    backendOnline: {
      type: Boolean,
      default: false,
    },
    historyCount: {
      type: Number,
      default: 0,
    },
  },
  emits: ['open-auth', 'open-history', 'open-health-config', 'logout'],
  template: `
    <header class="navbar">
      <div class="navbar-inner">
        <a href="#" class="brand" @click.prevent>
          <div class="brand-icon">M</div>
          <div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="brand-title">MarkItDown</span>
              <span class="brand-badge">PyTorch Router</span>
            </div>
            <div style="font-size: 11px; color: #64748b; font-weight: 500;">
              AI 文档智能转换与排版平台
            </div>
          </div>
        </a>

        <div class="nav-right">
          <!-- Backend Connectivity Status Pill -->
          <div
            :class="['health-pill', backendOnline ? 'online' : 'offline']"
            @click="$emit('open-health-config')"
            title="点击查看后端服务详情或配置 API 地址"
          >
            <span class="pulse-dot"></span>
            <span v-if="backendOnline">
              后端已连接
              <span v-if="backendHealth && backendHealth.classifier_loaded" style="font-weight: 700;">
                · DL 分类器就绪
              </span>
            </span>
            <span v-else>后端离线 (点击诊断)</span>
          </div>

          <!-- History Records Button -->
          <button class="btn btn-secondary btn-sm" @click="$emit('open-history')">
            📜 历史记录
            <span
              v-if="historyCount > 0"
              style="background: #e2e8f0; color: #334155; padding: 1px 6px; border-radius: 999px; font-size: 11px;"
            >
              {{ historyCount }}
            </span>
          </button>

          <!-- User Authentication Section -->
          <div v-if="user" class="user-capsule">
            <div class="user-avatar">{{ user.username.charAt(0).toUpperCase() }}</div>
            <span class="user-name">{{ user.username }}</span>
            <button
              class="btn btn-subtle btn-sm"
              style="padding: 2px 6px; font-size: 11px;"
              @click="$emit('logout')"
              title="退出登录"
            >
              退出
            </button>
          </div>

          <div v-else style="display: flex; align-items: center; gap: 8px;">
            <button class="btn btn-primary btn-sm" @click="$emit('open-auth')">
              🔐 登录 / 注册
            </button>
          </div>
        </div>
      </div>
    </header>
  `,
};
