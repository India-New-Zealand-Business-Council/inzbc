import { expect, test } from '@playwright/test'
import { RUN } from './support/platformApi'

/**
 * Browser contract regression for #129. The mock preserves server-like state across page.reload,
 * and rejects replayed transitions. It is NOT a real Postgres persistence/UAT test.
 * The real database-backed browser acceptance run remains separately required.
 */
test('run state survives refresh and stale start is refused by the mocked server', async ({ page }) => {
  let state = 'Draft'
  let version = 1
  let acceptedStarts = 0

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const { pathname } = new URL(request.url())
    const method = request.method()
    const run = { ...RUN, state, version }
    const reply = (body: unknown, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })

    if (pathname === '/api/session') {
      return reply({
        user_id: '00000000-0000-0000-0000-0000000000aa',
        name: 'Reviewer Test',
        roles: ['Analyst', 'Reviewer'],
        csrf_token: 'contract-test-token',
      })
    }
    if (pathname === '/api/dashboard') {
      return reply({
        run,
        gates: { qa_status: null, report_approval: null, distribution_authority: null, distribution_recipient: null },
        coverage: { total: 0, included: 0, by_verification: {} },
        open_actions: [],
        open_actions_truncated: false,
      })
    }
    if (pathname === '/api/runs' && method === 'GET') return reply([run])
    if (pathname === `/api/runs/${RUN.id}` && method === 'GET') return reply(run)
    if (pathname === `/api/runs/${RUN.id}/agent-rehearsals` && method === 'GET') return reply([])
    if (pathname === '/api/candidates' && method === 'GET') return reply([])
    if (pathname === '/api/source-library') return reply([])

    if (pathname === `/api/runs/${RUN.id}/start` && method === 'POST') {
      const body = request.postDataJSON() as { expected_version: number; reason: string; approval_ref: string }
      if (
        state !== 'Draft' ||
        body.expected_version !== version ||
        !body.reason?.trim() ||
        !body.approval_ref?.trim() ||
        request.headers()['x-csrf-token'] !== 'contract-test-token'
      ) {
        return reply({ detail: 'Illegal or stale transition' }, 409)
      }
      state = 'Run Authorised'
      version += 1
      acceptedStarts += 1
      return reply({ ...RUN, state, version })
    }
    return reply({ detail: 'Endpoint not mocked' }, 404)
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Runs & Candidates', exact: true }).click()
  await expect(page.getByText(RUN.run_number)).toBeVisible()
  await page.getByRole('button', { name: 'Start', exact: true }).click()
  await page.getByLabel('Reason').fill('Controlled fixture launch')
  await page.getByLabel(/Approval reference/).fill('TEST-AUTHORITY-ONLY')
  await page.getByRole('button', { name: 'Confirm Start' }).click()

  await expect(page.getByText('Run Authorised', { exact: true })).toBeVisible()
  expect(acceptedStarts).toBe(1)

  await page.reload()
  await page.getByRole('button', { name: 'Runs & Candidates', exact: true }).click()
  await expect(page.getByText('Run Authorised', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Start', exact: true })).toHaveCount(0)

  // Deliberately bypass the UI to prove that hiding an illegal action is NOT the gate.
  // page.evaluate() uses browser fetch, so Playwright's mocked server rejects the request.
  const illegalStatus = await page.evaluate(async (runId) => {
    const response = await fetch(`/api/runs/${runId}/start`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': 'contract-test-token' },
      body: JSON.stringify({
        expected_version: 1,
        reason: 'Attempt to replay',
        approval_ref: 'TEST-AUTHORITY-ONLY',
      }),
    })
    return response.status
  }, RUN.id)
  expect(illegalStatus).toBe(409)
  expect(acceptedStarts).toBe(1)
  await page.reload()
  await page.getByRole('button', { name: 'Runs & Candidates', exact: true }).click()
  await expect(page.getByText('Run Authorised', { exact: true })).toBeVisible()
})
