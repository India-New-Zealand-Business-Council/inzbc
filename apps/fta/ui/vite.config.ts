/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    // The API runs on its own origin in development. In deployment the public UI is served
    // from Cloudflare Pages and calls the Fly-hosted API cross-origin (ADR-0004), so the dev
    // proxy keeps the two shapes the same rather than hiding the boundary.
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      // Generated API types carry no logic; the drift check in CI is what guards them.
      exclude: ['src/api/schema.ts', 'src/main.tsx'],
      thresholds: {
        // Frontend gate is 80% per the plan; state and transition logic is held to 90%
        // as it lands. Presentational JSX is not worth chasing to 90%.
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
})
