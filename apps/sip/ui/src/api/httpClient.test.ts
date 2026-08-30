import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  apiRequest,
  isConcurrentModificationError,
  isUuid,
  isVerificationGateError,
  SipApiError,
} from './httpClient'

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

  it('throws SipApiError with the envelope message and code on a non-2xx response', async () => {
    mockFetch(
      { error: { status: 403, code: 'http_error', message: 'High signal requires a verified source' } },
      { ok: false, status: 403 },
    )
    await expect(apiRequest('/api/candidates/c1/score', {})).rejects.toMatchObject({
      message: 'High signal requires a verified source',
      status: 403,
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

  it('wraps a network failure as SipApiError', async () => {
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

  it('throws SipApiError when a 2xx response has an unreadable body', async () => {
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
})

describe('isVerificationGateError / isConcurrentModificationError', () => {
  it('matches only their own status code', () => {
    const gate = new SipApiError('nope', { status: 403 })
    const conflict = new SipApiError('stale', { status: 409 })
    expect(isVerificationGateError(gate)).toBe(true)
    expect(isVerificationGateError(conflict)).toBe(false)
    expect(isConcurrentModificationError(conflict)).toBe(true)
    expect(isConcurrentModificationError(gate)).toBe(false)
  })

  it('returns false for a non-SipApiError value', () => {
    expect(isVerificationGateError(new Error('plain'))).toBe(false)
    expect(isConcurrentModificationError('nope')).toBe(false)
  })
})

describe('isUuid', () => {
  it('accepts a well-formed UUID, case-insensitively, with surrounding whitespace trimmed', () => {
    expect(isUuid('34f4237b-ecd0-470c-8b2e-424ab745eb62')).toBe(true)
    expect(isUuid('34F4237B-ECD0-470C-8B2E-424AB745EB62')).toBe(true)
    expect(isUuid('  34f4237b-ecd0-470c-8b2e-424ab745eb62  ')).toBe(true)
  })

  it('rejects free text and malformed ids', () => {
    expect(isUuid('paras')).toBe(false)
    expect(isUuid('')).toBe(false)
    expect(isUuid('34f4237b-ecd0-470c-8b2e-424ab745eb6')).toBe(false)
  })
})

describe('CSRF', () => {
  it('adds the token to a write', async () => {
    // `write_access` refuses any non-GET with no `X-CSRF-Token`, so without this every write on
    // these screens is authenticated and refused. Added in `apiRequest` rather than in each
    // client so a new write cannot forget it.
    const spy = mockFetch({ ok: true })

    await apiRequest('/api/runs', { method: 'POST', body: '{}' })

    const [, init] = spy.mock.calls[0] as [string, RequestInit]
    expect((init.headers as Record<string, string>)['X-CSRF-Token']).toBe('a-real-token')
  })

  it('preserves the headers the caller set', async () => {
    const spy = mockFetch({ ok: true })

    await apiRequest('/api/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    })

    const [, init] = spy.mock.calls[0] as [string, RequestInit]
    expect(init.headers).toMatchObject({
      'Content-Type': 'application/json',
      'X-CSRF-Token': 'a-real-token',
    })
  })

  it.each(['GET', 'HEAD', 'OPTIONS'])('leaves a %s alone', async (method) => {
    // Requiring a token on a read would train callers to send it everywhere, and would make every
    // read depend on a second request it does not need.
    const spy = mockFetch([])

    await apiRequest('/api/runs', { method })

    const [, init] = spy.mock.calls[0] as [string, RequestInit]
    expect((init.headers as Record<string, string> | undefined)?.['X-CSRF-Token']).toBeUndefined()
  })

  it('treats a request with no method as a read', async () => {
    // `fetch` defaults to GET, so an omitted method must not be assumed to be a write.
    const spy = mockFetch([])

    await apiRequest('/api/runs', {})

    const [, init] = spy.mock.calls[0] as [string, RequestInit]
    expect((init.headers as Record<string, string> | undefined)?.['X-CSRF-Token']).toBeUndefined()
  })

  it('reads the session from the same origin the request goes to', async () => {
    // A caller using `baseUrl` for a cross-origin deployment must read its token from that host,
    // not from whatever page happens to be open.
    const { clearSession } = await import('./session')
    clearSession()
    const spy = vi.fn(async (url: string) =>
      url.endsWith('/api/session')
        ? {
            ok: true,
            status: 200,
            json: async () => ({
              user_id: 'u', name: 'n', roles: [], csrf_token: 'from-that-host',
            }),
          }
        : { ok: true, status: 200, json: async () => ({}) },
    )
    vi.stubGlobal('fetch', spy)

    await apiRequest('https://api.example.test/api/runs', { method: 'POST', body: '{}' })

    expect(spy.mock.calls[0]?.[0]).toBe('https://api.example.test/api/session')
  })
})
