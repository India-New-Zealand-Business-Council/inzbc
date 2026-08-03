/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// No dev proxy to a backend API (unlike apps/fta/ui, apps/sip/ui): this app is a static,
// link-out-only shell per docs/modules/member-portal-spec.md's build gate — it makes no API
// calls of its own, so there is nothing for a proxy to target yet.
export default defineConfig({
  plugins: [react(), tailwindcss()],
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
        // Matches the frontend gate used by apps/fta/ui, apps/sip/ui and apps/comms/ui.
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
})
