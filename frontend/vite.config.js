import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发模式下 /api 代理到本地后端（后端调试端口 18000，避开常用 8000）
// 生产环境由 Nginx 容器做同样的反代
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 9527,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:18000',
        changeOrigin: true,
      },
    },
  },
})
