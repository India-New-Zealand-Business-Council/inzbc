import { afterEach, describe, expect, it, vi } from 'vitest'
import { listRuns } from './runsClient'

const RUN = {
  id: 'run-1',
  run_number: 'RUN-20260808-01',
  state: 'Draft',
  version: 0,
  prompt_version: 'SIP-050 v1.1',
  coverage_start_utc: '2026-08-08T00:00:00Z',
  coverage_end_utc: '2026-08-08T23:59:59Z',
  initiated_by: '34f4237b-ecd0-470c-8b2e-424ab745eb62',
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

describe('listRuns', () => {
  it('GETs /api/runs and returns the list', async () => {
    const spy = mockFetch([RUN])
    await expect(listRuns()).resolves.toEqual([RUN])
    const [url, init] = firstCall(spy)
    expect(url).toBe('/api/runs')
    expect(init).toMatchObject({ credentials: 'same-origin' })
  })

  it('honours a baseUrl override', async () => {
    const spy = mockFetch([RUN])
    await listRuns({ baseUrl: 'http://127.0.0.1:8000' })
    const [url] = firstCall(spy)
    expect(url).toBe('http://127.0.0.1:8000/api/runs')
  })
})
