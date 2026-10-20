import { defineConfig, devices } from '@playwright/test'

/**
 * Runs against a server the caller already started — the `docker` CI job's own built image
 * (API + UI from one origin, per the Dockerfile) in CI, or `pnpm --filter @inzbc/fta-ui dev`
 * plus `uv run uvicorn services.api.main:app` locally. No `webServer` entry here: the FTA
 * path needs no database (see Dockerfile), so there is nothing this config could start on its
 * own that the caller hasn't already started more cheaply.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'line' : 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:8000',
    trace: 'on-first-retry',
  },
  projects: [
    // Explicit testMatch, not "everything else": without it this project would also pick up
    // reflow.spec.ts at the default desktop viewport, running the 320px case twice (once
    // meaninglessly) instead of only through the 320px-reflow project below.
    { name: 'chromium', testMatch: /fta-query\.spec\.ts/, use: { ...devices['Desktop Chrome'] } },
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
