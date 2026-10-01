import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发模式下 /api、/gateway 代理到本地服务（后端 18000、模拟网关 18001，均避开常用端口）
// 生产环境由 Nginx 做同样的反代
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 9527,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:18000',
        changeOrigin: true,
      },
      '/gateway': {
        target: 'http://127.0.0.1:18001',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/gateway/, ''),
      },
    },
  },
})
