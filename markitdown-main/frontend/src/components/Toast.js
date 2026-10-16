/**
 * Toast Notification system for MarkItDown.
 */
const { reactive } = window.Vue || (await import('https://cdn.jsdelivr.net/npm/vue@3/dist/vue.esm-browser.prod.js'));

export const toastState = reactive({
  toasts: [],
});

let toastId = 0;

export function showToast(message, type = 'info', duration = 3500) {
  const id = ++toastId;
  toastState.toasts.push({ id, message, type });

  setTimeout(() => {
    const idx = toastState.toasts.findIndex((t) => t.id === id);
    if (idx !== -1) {
      toastState.toasts.splice(idx, 1);
    }
  }, duration);
}

export const ToastComponent = {
  name: 'ToastContainer',
  setup() {
    return {
      toasts: toastState.toasts,
    };
  },
  template: `
    <div class="toast-container">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="['toast', toast.type]"
      >
        <span v-if="toast.type === 'success'">✅</span>
        <span v-else-if="toast.type === 'error'">❌</span>
        <span v-else-if="toast.type === 'warning'">⚠️</span>
        <span v-else>ℹ️</span>
        <span>{{ toast.message }}</span>
      </div>
    </div>
  `,
};
