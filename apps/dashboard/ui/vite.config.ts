/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Same-origin in deployment (ADR-0004); this proxy keeps the dev shape identical rather than
    // hiding the boundary. `GET /api/dashboard` (#47) is live behind this proxy — see
    // src/api/dashboardClient.ts.
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
      exclude: [
        // Entry point: one createRoot call, no logic.
        'src/main.tsx',
        // Generated from OpenAPI; the drift check in CI is what guards this, not tests.
        'src/api/schema.ts',
      ],
      thresholds: {
        // Matches the frontend gate used by apps/fta/ui, apps/comms/ui and apps/sip/ui.
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
})
