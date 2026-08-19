import { afterEach, describe, expect, it, vi } from 'vitest'
import { listCandidates } from './candidatesClient'

const CANDIDATE = {
  id: 'c1',
  run_id: 'run-1',
  headline: 'headline',
  source_id: null,
  url: null,
  summary: null,
  published_at: null,
  captured_at: '2026-08-08T01:00:00Z',
  in_coverage_window: true,
  nz_relevance: null,
  india_relevance: null,
  member_relevance: null,
  signal: null,
  confidence: null,
  verification: 'Unverified',
  duplicate_of: null,
  included: false,
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
  it('GETs /api/candidates scoped to the run, encoding the id', async () => {
    const spy = mockFetch([CANDIDATE])
    await expect(listCandidates('run 1')).resolves.toEqual([CANDIDATE])
    const [url, init] = firstCall(spy)
    expect(url).toBe('/api/candidates?run=run%201')
    expect(init).toMatchObject({ credentials: 'same-origin' })
  })

  it('honours a baseUrl override', async () => {
    const spy = mockFetch([CANDIDATE])
    await listCandidates('run-1', { baseUrl: 'http://127.0.0.1:8000' })
    const [url] = firstCall(spy)
    expect(url).toBe('http://127.0.0.1:8000/api/candidates?run=run-1')
  })
})
