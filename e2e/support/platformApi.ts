import type { Page, Route } from '@playwright/test'

/**
 * A stand-in for the API behind the platform shell (`apps/sip/ui`), so its screens can be driven
 * in a real browser without Postgres or a model key. Shapes follow `schemas/openapi.json`; a
 * route not listed answers 404 in the server's own error envelope, so a screen that calls
 * something unexpected shows its real error state rather than hanging.
 */

export const RUN = {
  id: 'run-1',
  run_number: 'SIP-2026-10-24',
  state: 'QA In Progress',
  version: 3,
  prompt_version: 'SIP-050 v1.1',
  coverage_start_utc: '2026-10-23T19:00:00+00:00',
  coverage_end_utc: '2026-10-24T19:00:00+00:00',
  initiated_by: '00000000-0000-0000-0000-0000000000aa',
  qa_status: null,
}

const SESSION = {
  user_id: '00000000-0000-0000-0000-0000000000aa',
  name: 'Priya Analyst',
  roles: ['Analyst', 'Reviewer'],
  csrf_token: 'e2e-csrf',
}

const DASHBOARD = {
  run: RUN,
  gates: { qa_status: null, report_approval: null, distribution_authority: null, distribution_recipient: null },
  coverage: { total: 4, included: 2, by_verification: { Verified: 2, Unverified: 2 } },
  open_actions: [],
  open_actions_truncated: false,
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
}

export interface PlatformApi {
  /** Questions the assistant received, newest last. */
  questions: string[]
}

export async function mockPlatformApi(page: Page): Promise<PlatformApi> {
  const api: PlatformApi = { questions: [] }
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url())
    const method = route.request().method()
    const path = url.pathname
    if (path === '/api/session') return json(route, SESSION)
    if (path === '/api/dashboard') return json(route, DASHBOARD)
    if (path === '/api/runs' && method === 'GET') return json(route, [RUN])
    if (path === `/api/runs/${RUN.id}` && method === 'GET') return json(route, RUN)
    if (path === `/api/runs/${RUN.id}/agent-rehearsals` && method === 'GET') return json(route, [])
    if (path === '/api/candidates' && method === 'GET') return json(route, [])
    if (path === '/api/source-library') return json(route, [])
    if (path === '/api/assistant/chat' && method === 'POST') {
      const body = route.request().postDataJSON() as { messages: { content: string }[] }
      api.questions.push(body.messages.at(-1)?.content ?? '')
      return json(route, {
        answer: `${RUN.run_number} is in QA In Progress.`,
        steps: [{ tool: 'list_runs', summary: 'Listed 1 run(s)' }],
        disclaimer: 'AI-generated and advisory.',
      })
    }
    return json(route, { error: { status: 404, code: 'http_error', message: `no mock for ${method} ${path}` } }, 404)
  })
  return api
}
