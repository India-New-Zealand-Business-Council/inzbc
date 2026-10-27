import { defineConfig, devices } from '@playwright/test'

/**
 * Runs against a server the caller already started — the `docker` CI job's own built image
 * (API + UI from one origin, per the Dockerfile) in CI, or `pnpm --filter @inzbc/fta-ui dev`
 * plus `uv run uvicorn services.api.main:app` locally. The FTA projects need no `webServer`:
 * the FTA path needs no database (see Dockerfile), so there is nothing this config could start
 * for them that the caller hasn't already started more cheaply. The platform project is the
 * exception: its shell is not in the image, so `webServer` builds and previews it.
 */
const PLATFORM_URL = 'http://127.0.0.1:4173'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'line' : 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:8000',
    trace: 'on-first-retry',
  },
  // Only the platform project uses this; the FTA projects run against the docker image the
  // caller started, as before.
  webServer: {
    command: 'pnpm --filter @inzbc/sip-ui build && pnpm --filter @inzbc/sip-ui preview --host 127.0.0.1 --port 4173 --strictPort',
    url: PLATFORM_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
  projects: [
    // Explicit testMatch, not "everything else": without it this project would also pick up
    // reflow.spec.ts at the default desktop viewport, running the 320px case twice (once
    // meaninglessly) instead of only through the 320px-reflow project below.
    { name: 'chromium', testMatch: /fta-(query|a11y)\.spec\.ts/, use: { ...devices['Desktop Chrome'] } },
    // The platform shell, served by `webServer` above with its API mocked in the spec
    // (e2e/support/platformApi.ts): it needs Postgres and a session the docker image has not got.
    {
      name: 'platform',
      testMatch: /(platform|platform-transition|keyboard)\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], baseURL: PLATFORM_URL },
    },
    {
      // Issue #100's own case: the 320px CSS reflow fix (#91) was verified once by hand, not
      // by CI, until this project exists. iPhone SE's layout viewport is exactly 375px, not
      // 320px (WCAG 2.2 Success Criterion 1.4.10's own reference width), so a custom viewport
      // rather than a named device preset.
      name: '320px-reflow',
      testMatch: /reflow\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], viewport: { width: 320, height: 640 } },
    },
  ],
})
