/**
 * Application Entrypoint (src/main.js).
 * Boots Vue 3 application and mounts onto #app container.
 */
import { AppComponent } from './App.js';

async function bootstrap() {
  const Vue = window.Vue || (await import('https://cdn.jsdelivr.net/npm/vue@3/dist/vue.esm-browser.prod.js'));
  const app = Vue.createApp(AppComponent);
  app.mount('#app');
}

bootstrap().catch((err) => {
  console.error('Failed to bootstrap MarkItDown Vue3 frontend:', err);
});
