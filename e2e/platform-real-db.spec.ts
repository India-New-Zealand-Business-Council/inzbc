import { expect, test } from '@playwright/test'

/**
 * Real-backend counterpart to #129's mocked regression (platform-transition.spec.ts). That spec
 * proves the *browser contract* against a mock that fakes server-like behaviour; this one proves
 * the same two claims — refresh survives, a stale transition is rejected — against the actual
 * API and a real Postgres row, closing the gap both #495 and #490 explicitly left open (#127).
 *
 * Not wired into the default `platform` Playwright project: it needs a real `vite dev` server
 * (for the `/api` proxy, see apps/sip/ui/vite.config.ts) and a live API + Postgres behind it,
 * neither of which the default project's build+preview `webServer` or the CI docker image carry
 * (see playwright.config.ts's own comment on why the platform project is mocked). Run it with
 * `e2e/real-db.config.ts` against a platform started by scripts/platform.ps1, or see
 * .github/workflows/sip-real-db-e2e.yml for the CI shape.
 *
 * Needs four env vars: E2E_BASE_URL (the vite dev server, default http://127.0.0.1:5173),
 * E2E_API_BASE_URL (default http://127.0.0.1:8000), E2E_SESSION_COOKIE and E2E_CSRF_TOKEN (a real
 * SIP Owner session — mint one with `python -m scripts.dev_session --github-login <login>`).
 */

// localhost, not 127.0.0.1: Vite binds localhost and ::1 only (see scripts/platform.ps1).
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:5173'
const API_BASE_URL = process.env.E2E_API_BASE_URL ?? 'http://127.0.0.1:8000'
const SESSION_COOKIE = process.env.E2E_SESSION_COOKIE
const CSRF_TOKEN = process.env.E2E_CSRF_TOKEN

test.skip(!SESSION_COOKIE || !CSRF_TOKEN, 'needs E2E_SESSION_COOKIE and E2E_CSRF_TOKEN — see file header')

test('a real run survives refresh and a real stale replay is rejected by Postgres, not just the UI', async ({
  page,
  request,
}) => {
  const authHeaders = { 'X-CSRF-Token': CSRF_TOKEN as string, cookie: `inzbc_session=${SESSION_COOKIE}` }

  // Create and launch-authorise a fresh run over the real API, so the test owns a row nothing
  // else is touching rather than racing seed data or another run of itself.
  const runNumber = `E2E-REAL-DB-${Date.now()}`
  const created = await request.post(`${API_BASE_URL}/api/runs`, {
    headers: authHeaders,
    data: {
      run_number: runNumber,
      prompt_version: 'SIP-050 v1.1',
      coverage_start_utc: new Date(Date.now() - 3600_000).toISOString(),
      coverage_end_utc: new Date().toISOString(),
    },
  })
  expect(created.ok(), await created.text()).toBeTruthy()
  const run = await created.json()

  const authorised = await request.post(`${API_BASE_URL}/api/runs/${run.id}/authorisations`, {
    headers: authHeaders,
    data: {
      kind: 'Launch',
      reason: 'Real-DB E2E regression for #127/#129',
      evidence_ref: 'e2e/platform-real-db.spec.ts',
      decided_at: new Date().toISOString(),
    },
  })
  expect(authorised.ok(), await authorised.text()).toBeTruthy()
  const authorisation = await authorised.json()

  const started = await request.post(`${API_BASE_URL}/api/runs/${run.id}/start`, {
    headers: authHeaders,
    data: { expected_version: run.version, reason: 'Real-DB E2E launch', approval_ref: authorisation.id },
  })
  expect(started.ok(), await started.text()).toBeTruthy()

  // Browser side: a real session cookie, no mocked route. The dev proxy forwards whatever cookie
  // the browser sends, so this is the same network path a real signed-in user takes.
  await page.context().addCookies([
    { name: 'inzbc_session', value: SESSION_COOKIE as string, domain: new URL(BASE_URL).hostname, path: '/' },
  ])
  await page.goto(BASE_URL)
  await page.getByRole('button', { name: 'Runs & Candidates', exact: true }).click()
  // The run just launched through this same session is already the server's working run —
  // no "Work this run" click needed, and asserting that directly is the real claim under test.
  const card = page.locator('li', { hasText: runNumber }).first()
  await expect(card.getByText('Working run')).toBeVisible()
  await expect(card.getByText('Run Authorised', { exact: true })).toBeVisible()

  await page.reload()
  await page.getByRole('button', { name: 'Runs & Candidates', exact: true }).click()
  const cardAfterReload = page.locator('li', { hasText: runNumber }).first()
  await expect(cardAfterReload.getByText('Working run')).toBeVisible()
  await expect(cardAfterReload.getByText('Run Authorised', { exact: true })).toBeVisible()

  // The real gate, not the UI's: replay the same launch with the version it already consumed.
  const replay = await request.post(`${API_BASE_URL}/api/runs/${run.id}/start`, {
    headers: authHeaders,
    data: { expected_version: run.version, reason: 'Replay attempt', approval_ref: authorisation.id },
  })
  expect(replay.status()).toBe(409)
})
