import { vi } from 'vitest'

export function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response
}

/** Stands in for `POST /api/reports`, `POST /api/reports/:id/qa` and `POST /api/runs/:id/fail-qa`
 * — the three real endpoints `submitReportForQa`/`submitQaResult` call. Shared by reportsStore's
 * own tests and by screen tests that exercise those functions unmocked (BriefBuilderScreen,
 * QaReviewScreen) — same stub either way, since it's standing in for the same three endpoints. */
export function stubReportsFetch(): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.signal?.aborted) throw new DOMException('Aborted', 'AbortError')
      if (url === '/api/reports' && init?.method === 'POST') {
        return jsonResponse({
          id: 'rv-1',
          run_id: 'RUN-1',
          version_number: 1,
          created_by: 'test',
          content_sha256: '0'.repeat(64),
          created_at: new Date().toISOString(),
          submitted_at: new Date().toISOString(),
        })
      }
      if (url.endsWith('/qa') && init?.method === 'POST') {
        return jsonResponse({ report_version_id: 'rv-1', qa_status: 'Pass', critical_failures: 0 })
      }
      if (url.endsWith('/fail-qa') && init?.method === 'POST') {
        return jsonResponse({ id: 'RUN-1', state: 'QA Failed', version: 1 })
      }
      throw new Error(`Unexpected fetch in test: ${url}`)
    }),
  )
}
