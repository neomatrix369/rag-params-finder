import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

const devProxyTarget =
  process.env.VITE_DEV_PROXY_TARGET?.trim() || 'http://127.0.0.1:8001'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    reporters: ['default', ['junit', { outputFile: '../.test-results/frontend-junit.xml' }]],
    coverage: {
      provider: 'v8',
      reportsDirectory: '../.reports/coverage/frontend',
      reporter: ['text', 'json', 'html'],
      // Floor = post–Should re-measure 2026-07-27 (Slice 44). Started at pre-test
      // baseline (lines 50.18%); ratcheted after apiClient/fetch/status/control tests.
      // Do not lower without a Decision Log row.
      thresholds: {
        statements: 62,
        branches: 58,
        functions: 61,
        lines: 64,
      },
    },
  },
  server: {
    port: 5374,
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
