import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Same-origin `/api/*` → FastAPI on IPv4 loopback (avoids browser resolving
      // `localhost` → ::1 while uvicorn listens only on 127.0.0.1 — a common macOS mishap).
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
