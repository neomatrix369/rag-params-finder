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
      // Shared FE+BE product floors (DECISIONS #142): stmts/funcs/lines ≥95, branches ≥90.
      // Backend: fail_under=95 + scripts/check_backend_coverage_floors.py (95/90/n/a/95).
      // Do not change without a Decision Log row.
      all: true,
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/test/**',
        'src/main.tsx',
        'src/types/**',
      ],
      thresholds: {
        statements: 95,
        branches: 90,
        functions: 95,
        lines: 95,
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
