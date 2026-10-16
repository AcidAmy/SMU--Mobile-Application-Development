/**
 * JWT Authentication Modal (Login / Register).
 */
import { authApi } from '../api/auth.js';
import { showToast } from './Toast.js';

const { ref, reactive } = window.Vue || (await import('https://cdn.jsdelivr.net/npm/vue@3/dist/vue.esm-browser.prod.js'));

export const AuthModalComponent = {
  name: 'AuthModal',
  emits: ['close', 'auth-success'],
  setup(props, { emit }) {
    const activeTab = ref('login'); // 'login' | 'register'
    const loading = ref(false);
    const errorMessage = ref('');

    const loginForm = reactive({
      username: '',
      password: '',
    });

    const registerForm = reactive({
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
    });

    const closeModal = () => {
      emit('close');
    };

    const handleLogin = async () => {
      errorMessage.value = '';
      if (!loginForm.username.trim() || !loginForm.password) {
        errorMessage.value = '请输入用户名和密码';
        return;
      }

      loading.value = true;
      try {
        const res = await authApi.login(loginForm.username.trim(), loginForm.password);
        showToast(`欢迎回来，${res.user ? res.user.username : loginForm.username}！`, 'success');
        emit('auth-success', res.user);
        closeModal();
      } catch (err) {
        errorMessage.value = err.message || '登录失败，请检查账号与密码';
      } finally {
        loading.value = false;
      }
    };

    const handleRegister = async () => {
      errorMessage.value = '';
      if (registerForm.username.trim().length < 3) {
        errorMessage.value = '用户名长度不能少于 3 个字符';
        return;
      }
      if (registerForm.password.length < 6) {
        errorMessage.value = '密码长度不能少于 6 个字符';
        return;
      }
      if (registerForm.password !== registerForm.confirmPassword) {
        errorMessage.value = '两次输入的密码不一致';
        return;
      }

      loading.value = true;
      try {
        await authApi.register(
          registerForm.username.trim(),
          registerForm.password,
          registerForm.email
        );
        showToast('账号注册成功！正在自动登录...', 'success');

        // Auto login after successful registration
        const loginRes = await authApi.login(
          registerForm.username.trim(),
          registerForm.password
        );
        emit('auth-success', loginRes.user);
        closeModal();
      } catch (err) {
        errorMessage.value = err.message || '注册失败，该用户名可能已被占用';
      } finally {
        loading.value = false;
      }
    };

    return {
      activeTab,
      loading,
      errorMessage,
      loginForm,
      registerForm,
      closeModal,
      handleLogin,
      handleRegister,
    };
  },
  template: `
    <div class="modal-overlay" @click.self="closeModal">
      <div class="modal-card">
        <div class="modal-header">
          <div class="modal-title">
            {{ activeTab === 'login' ? '用户登录' : '新用户注册' }}
          </div>
          <button class="modal-close" @click="closeModal" title="关闭">&times;</button>
        </div>

        <div class="modal-body">
          <div class="auth-tabs">
            <button
              :class="['auth-tab', activeTab === 'login' ? 'active' : '']"
              @click="activeTab = 'login'; errorMessage = ''"
            >
              账号登录
            </button>
            <button
              :class="['auth-tab', activeTab === 'register' ? 'active' : '']"
              @click="activeTab = 'register'; errorMessage = ''"
            >
              注册新用户
            </button>
          </div>

          <!-- Error Alert Banner -->
          <div
            v-if="errorMessage"
            style="background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px;"
          >
            <span>⚠️</span>
            <span>{{ errorMessage }}</span>
          </div>

          <!-- Login Form -->
          <form v-if="activeTab === 'login'" @submit.prevent="handleLogin">
            <div class="form-group">
              <label class="form-label">用户名</label>
              <input
                v-model="loginForm.username"
                type="text"
                class="form-input"
                placeholder="请输入用户名"
                required
                autocomplete="username"
              />
            </div>

            <div class="form-group">
              <label class="form-label">密码</label>
              <input
                v-model="loginForm.password"
                type="password"
                class="form-input"
                placeholder="请输入密码"
                required
                autocomplete="current-password"
              />
            </div>

            <div style="margin-top: 24px;">
              <button
                type="submit"
                class="btn btn-primary"
                style="width: 100%; padding: 10px;"
                :disabled="loading"
              >
                <span v-if="loading">正在登录...</span>
                <span v-else>立即登录</span>
              </button>
            </div>

            <div style="text-align: center; margin-top: 14px; font-size: 12px; color: #64748b;">
              没有账号？
              <a href="#" style="color: #2563eb; text-decoration: none; font-weight: 600;" @click.prevent="activeTab = 'register'; errorMessage = ''">
                免费注册
              </a>
            </div>
          </form>

          <!-- Register Form -->
          <form v-else @submit.prevent="handleRegister">
            <div class="form-group">
              <label class="form-label">用户名</label>
              <input
                v-model="registerForm.username"
                type="text"
                class="form-input"
                placeholder="3~50 位字符"
                required
                autocomplete="username"
              />
            </div>

            <div class="form-group">
              <label class="form-label">电子邮箱 (选填)</label>
              <input
                v-model="registerForm.email"
                type="email"
                class="form-input"
                placeholder="name@example.com"
                autocomplete="email"
              />
            </div>

            <div class="form-group">
              <label class="form-label">登录密码</label>
              <input
                v-model="registerForm.password"
                type="password"
                class="form-input"
                placeholder="不少于 6 位"
                required
                autocomplete="new-password"
              />
            </div>

            <div class="form-group">
              <label class="form-label">确认密码</label>
              <input
                v-model="registerForm.confirmPassword"
                type="password"
                class="form-input"
                placeholder="请再次输入密码"
                required
                autocomplete="new-password"
              />
            </div>

            <div style="margin-top: 24px;">
              <button
                type="submit"
                class="btn btn-primary"
                style="width: 100%; padding: 10px;"
                :disabled="loading"
              >
                <span v-if="loading">正在注册...</span>
                <span v-else>创建账号并自动登录</span>
              </button>
            </div>

            <div style="text-align: center; margin-top: 14px; font-size: 12px; color: #64748b;">
              已有账号？
              <a href="#" style="color: #2563eb; text-decoration: none; font-weight: 600;" @click.prevent="activeTab = 'login'; errorMessage = ''">
                直接登录
              </a>
            </div>
          </form>
        </div>
      </div>
    </div>
  `,
};
