import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  captureCandidate,
  getCandidate,
  listCandidates,
  mergeCandidate,
  routeCandidate,
  scoreCandidate,
  verifyCandidate,
} from './candidatesClient'

const CANDIDATE = {
  id: 'cand-1',
  run_id: 'run-1',
  headline: 'Test candidate',
  source_id: null,
  url: null,
  summary: null,
  published_at: null,
  captured_at: '2026-08-08T00:00:00Z',
  in_coverage_window: null,
  nz_relevance: null,
  india_relevance: null,
  member_relevance: null,
  signal: null,
  confidence: null,
  verification: 'Unverified',
  duplicate_of: null,
  included: null,
  reason: null,
  proposed_routing: null,
}

/** First call's [url, init]. Narrowed because noUncheckedIndexedAccess is on. */
function firstCall(spy: ReturnType<typeof vi.fn>): [string, RequestInit] {
  const call = spy.mock.calls[0]
  if (!call) throw new Error('fetch was not called')
  return [String(call[0]), call[1] as RequestInit]
}

function mockFetch(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  const { ok = true, status = 200 } = init
  const spy = vi.fn().mockResolvedValue({ ok, status, json: async () => body })
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => vi.unstubAllGlobals())

describe('listCandidates', () => {
  it('GETs /api/candidates?run=:id, encoding the run id', async () => {
    const spy = mockFetch([CANDIDATE])
    await listCandidates('run 1')
    const [url] = firstCall(spy)
    expect(url).toBe('/api/candidates?run=run%201')
  })
})

describe('getCandidate / captureCandidate', () => {
  it('GETs /api/candidates/:id', async () => {
    const spy = mockFetch(CANDIDATE)
    await getCandidate('cand-1')
    const [url] = firstCall(spy)
    expect(url).toBe('/api/candidates/cand-1')
  })

  it('POSTs a new candidate', async () => {
    const spy = mockFetch(CANDIDATE, { status: 201 })
    await captureCandidate({
      run_id: 'run-1',
      headline: 'Test candidate',
    })
    const [url, init] = firstCall(spy)
    expect(url).toBe('/api/candidates')
    expect(init.method).toBe('POST')
    expect(JSON.parse(String(init.body))).toMatchObject({ run_id: 'run-1' })
  })
})

describe('candidate commands', () => {
  const actor = { reason: 'go' }

  it('verify posts to /verify', async () => {
    const spy = mockFetch({ ...CANDIDATE, verification: 'Verified' })
    await verifyCandidate('cand-1', { verification: 'Verified', ...actor })
    const [url] = firstCall(spy)
    expect(url).toBe('/api/candidates/cand-1/verify')
  })

  it('score posts to /score', async () => {
    const spy = mockFetch({ ...CANDIDATE, signal: 'Low' })
    await scoreCandidate('cand-1', { signal: 'Low', ...actor })
    const [url] = firstCall(spy)
    expect(url).toBe('/api/candidates/cand-1/score')
  })

  it('score surfaces the verification-gate 403 distinctly', async () => {
    mockFetch(
      {
        error: {
          status: 403,
          code: 'http_error',
          message: 'High signal requires a verified source (got verification=Unverified)',
        },
      },
      { ok: false, status: 403 },
    )
    await expect(scoreCandidate('cand-1', { signal: 'High', ...actor })).rejects.toMatchObject({
      status: 403,
      message: expect.stringContaining('requires a verified source'),
    })
  })

  it('route posts to /route', async () => {
    const spy = mockFetch({ ...CANDIDATE, included: true })
    await routeCandidate('cand-1', { included: true, ...actor })
    const [url] = firstCall(spy)
    expect(url).toBe('/api/candidates/cand-1/route')
  })

  it('merge posts to /merge', async () => {
    const spy = mockFetch({ ...CANDIDATE, duplicate_of: 'cand-2', included: false })
    await mergeCandidate('cand-1', { duplicate_of: 'cand-2', ...actor })
    const [url] = firstCall(spy)
    expect(url).toBe('/api/candidates/cand-1/merge')
  })

  it('merge surfaces a self-merge 400 as SipApiError', async () => {
    mockFetch(
      { error: { status: 400, code: 'http_error', message: 'cannot merge a candidate into itself' } },
      { ok: false, status: 400 },
    )
    await expect(mergeCandidate('cand-1', { duplicate_of: 'cand-1', ...actor })).rejects.toMatchObject({
      status: 400,
    })
  })
})
