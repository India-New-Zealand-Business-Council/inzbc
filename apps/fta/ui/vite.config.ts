/// <reference types="vitest/config" />
import { reticle } from '@reticlehq/vite-plugin'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Reticle drives the running app through a browser for manual verification. It belongs in `vite
// dev` and nowhere else, so it is added only for `serve` and never under Vitest.
//
// Both halves of that condition were earned rather than assumed. The installer added `reticle()`
// unconditionally and all four Vitest workers then timed out on startup, taking 33 passing tests
// with them: Vitest also runs as `serve`, so `command` alone does not separate them. A production
// build was clean either way, but keeping it out of `build` says the intent rather than relying on
// the plugin to keep opting out.
const devOnlyPlugins = (command: string) =>
  command === 'serve' && !process.env.VITEST ? [reticle()] : []

export default defineConfig(({ command }) => ({
  plugins: [...devOnlyPlugins(command), react(), tailwindcss()],
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
      exclude: [
        // Generated from OpenAPI; the drift check in CI is what guards this, not tests.
        'src/api/schema.ts',
        // Entry point: one createRoot call, no logic.
        'src/main.tsx',
        // Stories are exercised by Storybook (and Chromatic when it lands), not by Vitest.
        // Counting them here measures nothing and pushes toward writing tests for fixtures.
        '**/*.stories.tsx',
      ],
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
}))
