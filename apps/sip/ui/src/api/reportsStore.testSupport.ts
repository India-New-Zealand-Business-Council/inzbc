import { vi } from 'vitest'

export function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response
}

/** Stands in for `POST /api/reports`, `GET /api/reports/:id`, `POST /api/reports/:id/qa`,
 * `POST /api/reports/:id/ruling` / `/approval` / `/distribution`, and `POST /api/runs/:id/fail-qa`
 * — every real endpoint `reportsStore.ts` calls. Shared by reportsStore's own tests and by screen
 * tests that exercise those functions unmocked (BriefBuilderScreen, QaReviewScreen), same stub
 * either way, since it's standing in for the same endpoints. Stateless: every GET reports revision
 * 0 for every stream, every decision POST returns stream_revision 1 — enough to prove a screen
 * wires to the real calls, not a re-test of the optimistic-concurrency conflict itself, which
 * `services/api/tests/test_reports_api.py` already covers against the real repository. */
export interface StubReportsFetchOptions {
  /** Overrides the GET /api/reports/:id decisions block — e.g. `{ report_approval: 'Approved',
   * ceo_ruling: 'Continue' }` to stand in for an approval some other client already recorded
   * out-of-band (services/api/reports.py's `recordCeoDecision` doc comment: this UI never builds
   * that control itself). Defaults to every stream undecided, the real default state and the one
   * that matches `fetchDistributionReadiness` refusing until something else records approval. */
  decisions?: Partial<{
    ceo_ruling: string | null
    report_approval: string | null
    distribution_authority: string | null
    distribution_recipient: string | null
  }>
}

export function stubReportsFetch(options: StubReportsFetchOptions = {}): void {
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
      if (/^\/api\/reports\/[^/]+$/.test(url) && (!init?.method || init.method === 'GET')) {
        return jsonResponse({
          report: {
            id: 'rv-1',
            run_id: 'RUN-1',
            version_number: 1,
            created_by: 'test',
            content_sha256: '0'.repeat(64),
            created_at: new Date().toISOString(),
            submitted_at: new Date().toISOString(),
          },
          decisions: {
            ceo_ruling: null,
            report_approval: null,
            distribution_authority: null,
            distribution_recipient: null,
            ...options.decisions,
            revisions: { 'CEO Ruling': 0, 'Report Approval': 0, 'Distribution Authority': 0 },
          },
        })
      }
      if (url.endsWith('/qa') && init?.method === 'POST') {
        return jsonResponse({ report_version_id: 'rv-1', qa_status: 'Pass', critical_failures: 0 })
      }
      if (url.endsWith('/fail-qa') && init?.method === 'POST') {
        return jsonResponse({ id: 'RUN-1', state: 'QA Failed', version: 1 })
      }
      const decisionMatch = /\/(ruling|approval|distribution)$/.exec(url)
      if (decisionMatch && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)) as { value: string }
        const kind = { ruling: 'CEO Ruling', approval: 'Report Approval', distribution: 'Distribution Authority' }[
          decisionMatch[1] as 'ruling' | 'approval' | 'distribution'
        ]
        return jsonResponse({
          id: 'dr-1',
          stream_id: 'ds-1',
          report_version_id: 'rv-1',
          kind,
          stream_revision: 1,
          value: body.value,
          actor_id: 'test',
          decided_at: new Date().toISOString(),
          reason: 'test',
        })
      }
      throw new Error(`Unexpected fetch in test: ${url}`)
    }),
  )
}
