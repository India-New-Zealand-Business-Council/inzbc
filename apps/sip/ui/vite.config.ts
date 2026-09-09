/// <reference types="vitest/config" />
import { fileURLToPath } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const appSrc = (name: string) =>
  fileURLToPath(new URL(`../../${name}/ui/src`, import.meta.url))

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // The four module UIs are separate Vite apps that each ship one screen. The platform shell
    // mounts them as tabs rather than running five dev servers, so it needs their sources on the
    // module graph. Aliases rather than workspace packages: none of them declare an entry point
    // or build a library bundle, and adding that plumbing would be four package.json rewrites to
    // reach code already sitting in this repo.
    alias: {
      '@fta': appSrc('fta'),
      '@comms': appSrc('comms'),
      '@dashboard': appSrc('dashboard'),
      '@member': appSrc('member'),
    },
  },
  server: {
    // Same-origin in deployment (ADR-0004); this proxy keeps the dev shape identical rather than
    // hiding the boundary. `/api/runs` and `/api/candidates` are live behind this proxy today
    // (#237, #242) — see src/api/runsClient.ts and candidatesClient.ts. The report/decision/
    // dashboard endpoints the other four screens target are still unbuilt (issue #44), so
    // src/api/reportsStore.ts stays fixture-backed for those.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // Attach a dev session when one was minted, so a local run shows real data instead of an
        // error box where the run status belongs. Every business route requires a session, which
        // is correct, and a browser here cannot complete the GitHub handshake that would normally
        // supply one.
        //
        // This is a dev-server seam, not a bypass. `server.proxy` exists only while `vite dev` is
        // running: it is absent from every build, so there is no branch in shipped code that must
        // never be reachable. The session itself is real -- scripts/dev_session.py mints it
        // through the same SessionRepository the OAuth callback uses, against the same allowlist.
        configure: (proxy) => {
          const session = process.env.INZBC_DEV_SESSION
          if (!session) return
          proxy.on('proxyReq', (proxyReq) => {
            const existing = proxyReq.getHeader('cookie')
            // Appended rather than replacing: a real browser session, once one exists, must win
            // over the injected one instead of being silently overwritten.
            proxyReq.setHeader(
              'cookie',
              existing ? `${existing}; inzbc_session=${session}` : `inzbc_session=${session}`,
            )
          })
        },
      },
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
