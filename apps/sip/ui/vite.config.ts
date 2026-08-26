/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Same-origin in deployment (ADR-0004); this proxy keeps the dev shape identical rather than
    // hiding the boundary. `/api/runs` and `/api/candidates` are live behind this proxy today
    // (#237, #242) — see src/api/runsClient.ts and candidatesClient.ts. The report/decision/
    // dashboard endpoints the other four screens target are still unbuilt (issue #44), so
    // src/api/reportsStore.ts stays fixture-backed for those.
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    // BriefBuilderScreen renders one row per SIP-185 mandatory source (112, not the 8-row
    // placeholder this fixture used to carry — see lib/fixtures.ts) — comfortably fast in
    // isolation, but the full workspace suite runs every screen's tests concurrently, and CPU
    // contention across those worker threads can push a 112-row render past the 5s default.
    testTimeout: 20000,
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
        // Matches the frontend gate used by apps/fta/ui and apps/comms/ui.
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
})
