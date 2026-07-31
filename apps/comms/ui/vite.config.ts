/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // The API runs on its own origin in development; same-origin in deployment (ADR-0004). See
    // apps/fta/ui/vite.config.ts for the identical rationale — this proxy keeps the two shapes
    // the same rather than hiding the boundary. Note: /api/comms/draft is a proposed contract
    // (docs/api-integration-spec.md) — nothing is listening on the API side yet (issue #65).
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
        // Matches the frontend gate used by apps/fta/ui.
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
})
