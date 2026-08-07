import { afterEach, describe, expect, it, vi } from 'vitest'
import { completeRun, createRun, getRun, listRuns, nextAction, pauseRun, resumeRun, startRun } from './runsClient'

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

describe('listRuns / getRun', () => {
  it('GETs /api/runs and returns the list', async () => {
    const spy = mockFetch([RUN])
    await expect(listRuns()).resolves.toEqual([RUN])
    const [url, init] = firstCall(spy)
    expect(url).toBe('/api/runs')
    expect(init).toMatchObject({ credentials: 'same-origin' })
  })

  it('GETs /api/runs/:id, encoding the id', async () => {
    const spy = mockFetch(RUN)
    await getRun('run 1')
    const [url] = firstCall(spy)
    expect(url).toBe('/api/runs/run%201')
  })

  it('honours a baseUrl override', async () => {
    const spy = mockFetch([RUN])
    await listRuns({ baseUrl: 'http://127.0.0.1:8000' })
    const [url] = firstCall(spy)
    expect(url).toBe('http://127.0.0.1:8000/api/runs')
  })
})

describe('createRun', () => {
  it('POSTs the body as JSON', async () => {
    const spy = mockFetch(RUN, { status: 201 })
    await createRun({
      run_number: 'RUN-20260808-01',
      prompt_version: 'SIP-050 v1.1',
      coverage_start_utc: '2026-08-08T00:00:00Z',
      coverage_end_utc: '2026-08-08T23:59:59Z',
      initiated_by: '34f4237b-ecd0-470c-8b2e-424ab745eb62',
    })
    const [url, init] = firstCall(spy)
    expect(url).toBe('/api/runs')
    expect(init.method).toBe('POST')
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json')
    expect(JSON.parse(String(init.body))).toMatchObject({ run_number: 'RUN-20260808-01' })
  })
})

describe('lifecycle transitions', () => {
  const body = { expected_version: 0, actor_id: '34f4237b-ecd0-470c-8b2e-424ab745eb62', reason: 'go' }

  it.each([
    ['start', startRun, 'Run Authorised'],
    ['pause', pauseRun, 'Paused'],
    ['resume', resumeRun, 'Coverage Locked'],
    ['complete', completeRun, 'Closed'],
  ] as const)('%s posts to /api/runs/:id/%s', async (action, fn, resultState) => {
    const spy = mockFetch({ ...RUN, state: resultState, version: 1 })
    const result = await fn('run-1', body)
    const [url, init] = firstCall(spy)
    expect(url).toBe(`/api/runs/run-1/${action}`)
    expect(init.method).toBe('POST')
    expect(result.state).toBe(resultState)
  })

  it('surfaces a 409 as SipApiError so a stale caller can re-fetch', async () => {
    mockFetch(
      { error: { status: 409, code: 'http_error', message: 'version mismatch' } },
      { ok: false, status: 409 },
    )
    await expect(startRun('run-1', body)).rejects.toMatchObject({ status: 409 })
  })

  it('surfaces a 403 (missing/invalid approval_ref) as SipApiError', async () => {
    mockFetch(
      { error: { status: 403, code: 'http_error', message: 'no approval_ref' } },
      { ok: false, status: 403 },
    )
    await expect(startRun('run-1', body)).rejects.toMatchObject({ status: 403, message: 'no approval_ref' })
  })
})

describe('nextAction', () => {
  it.each([
    ['Draft', 'start'],
    ['Awaiting CEO Decision', 'pause'],
    ['Paused', 'resume'],
    ['Distributed', 'complete'],
    ['Closed', null],
    ['Scanning', null],
  ] as const)('%s -> %s', (state, expected) => {
    expect(nextAction(state)).toBe(expected)
  })
})
