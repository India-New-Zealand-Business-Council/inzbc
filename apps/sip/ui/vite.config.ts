/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Same-origin in deployment (ADR-0004); this proxy keeps the dev shape identical rather than
    // hiding the boundary. Nothing is listening on the API side yet — the SIP report endpoints
    // land once the database and orchestrator persistence exist (issue #44), so this UI is built
    // against contract fixtures (src/api/reportsStore.ts), not this proxy, for now.
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
      ],
      thresholds: {
        // Matches the frontend gate used by apps/fta/ui and apps/comms/ui.
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
})
