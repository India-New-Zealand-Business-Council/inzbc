import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiRequest, DashboardApiError } from './httpClient'

function mockFetch(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  const { ok = true, status = 200 } = init
  const spy = vi.fn().mockResolvedValue({ ok, status, json: async () => body })
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => vi.unstubAllGlobals())

describe('apiRequest', () => {
  it('returns the parsed body on a 2xx response', async () => {
    mockFetch({ id: 'run-1' })
    await expect(apiRequest('/api/runs/run-1', {})).resolves.toEqual({ id: 'run-1' })
  })

  it('throws DashboardApiError with the envelope message and code on a non-2xx response', async () => {
    mockFetch(
      { error: { status: 404, code: 'http_error', message: 'no run found' } },
      { ok: false, status: 404 },
    )
    await expect(apiRequest('/api/runs/missing', {})).rejects.toMatchObject({
      message: 'no run found',
      status: 404,
      code: 'http_error',
    })
  })

  it('falls back to a generic message when the body is not the error envelope shape', async () => {
    mockFetch({ detail: 'unexpected shape' }, { ok: false, status: 500 })
    await expect(apiRequest('/api/runs', {})).rejects.toMatchObject({
      message: 'SIP service returned 500.',
      status: 500,
    })
  })

  it('wraps a network failure as DashboardApiError', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('fetch failed')))
    await expect(apiRequest('/api/runs', {})).rejects.toMatchObject({
      message: 'Could not reach the SIP service.',
    })
  })

  it('rethrows AbortError as-is, not wrapped', async () => {
    const abortError = new DOMException('Aborted', 'AbortError')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abortError))
    await expect(apiRequest('/api/runs', {})).rejects.toBe(abortError)
  })

  it('throws DashboardApiError when a 2xx response has an unreadable body', async () => {
    const spy = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new Error('bad json')
      },
    })
    vi.stubGlobal('fetch', spy)
    await expect(apiRequest('/api/runs', {})).rejects.toMatchObject({
      message: 'SIP service returned an unreadable response.',
    })
  })

  it('throws DashboardApiError with the status when a non-2xx response has an unreadable body', async () => {
    const spy = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => {
        throw new Error('bad json')
      },
    })
    vi.stubGlobal('fetch', spy)
    await expect(apiRequest('/api/runs', {})).rejects.toMatchObject({
      message: 'SIP service returned 503.',
      status: 503,
    })
  })
})

describe('DashboardApiError', () => {
  it('carries status and code through to the instance', () => {
    const error = new DashboardApiError('nope', { status: 403, code: 'forbidden' })
    expect(error.name).toBe('DashboardApiError')
    expect(error.status).toBe(403)
    expect(error.code).toBe('forbidden')
  })
})
