import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const devProxyTarget =
  process.env.VITE_DEV_PROXY_TARGET?.trim() || 'http://127.0.0.1:8001'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Same-origin `/api/*` → FastAPI (127.0.0.1 on host; `server` service name in Docker dev).
      '/api': {
        target: devProxyTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
