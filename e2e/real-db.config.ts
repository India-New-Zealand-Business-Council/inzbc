import { defineConfig, devices } from '@playwright/test'

/**
 * Separate from playwright.config.ts on purpose. That config's `platform` project is mocked
 * precisely because its shared `webServer` (build + `vite preview`) has no database and no
 * session behind it — see its own comment. This one instead expects the caller to already have a
 * real platform running (scripts/platform.ps1, or sip-real-db-e2e.yml's CI steps) and a minted
 * session in E2E_SESSION_COOKIE/E2E_CSRF_TOKEN, so it starts nothing and mocks nothing.
 */
export default defineConfig({
  testDir: '.',
  testMatch: /platform-real-db\.spec\.ts/,
  fullyParallel: false,
  retries: 0,
  reporter: process.env.CI ? 'line' : 'list',
  use: {
    // localhost, not 127.0.0.1: Vite binds localhost and ::1 only (see scripts/platform.ps1).
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    trace: 'on-first-retry',
    ...devices['Desktop Chrome'],
  },
})
