import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  clearSession,
  getCsrfToken,
  getSession,
  NotSignedInError,
  SessionUnavailableError,
} from './session'

const VALID_BODY = {
  user_id: '00000000-0000-0000-0000-0000000000aa',
  name: 'Test Principal',
  roles: ['Secretariat'],
  csrf_token: 'a-real-token',
}

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

beforeEach(() => {
  clearSession()
})

afterEach(() => {
  vi.restoreAllMocks()
  clearSession()
})

describe('getSession', () => {
  it('returns the session and its CSRF token', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(VALID_BODY)))

    await expect(getSession()).resolves.toEqual({
      userId: VALID_BODY.user_id,
      name: 'Test Principal',
      roles: ['Secretariat'],
      csrfToken: 'a-real-token',
    })
  })

  it('sends the cookie, because the token is only readable with it', async () => {
    const fetchMock = vi.fn(async () => jsonResponse(VALID_BODY))
    vi.stubGlobal('fetch', fetchMock)

    await getSession()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/session',
      expect.objectContaining({ credentials: 'same-origin' }),
    )
  })

  it('fetches once however many callers ask', async () => {
    // Caching the promise rather than the value is what makes this hold. Caching the value would
    // leave a window where a second caller starts a second request because the first has not
    // resolved yet, which is the common case when a screen fires two writes at once.
    const fetchMock = vi.fn(async () => jsonResponse(VALID_BODY))
    vi.stubGlobal('fetch', fetchMock)

    await Promise.all([getSession(), getSession(), getCsrfToken()])

    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('throws NotSignedInError on 401, distinctly from other failures', async () => {
    // Signing in fixes one of these and not the other, so a caller has to be able to tell them
    // apart to say anything useful.
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(null, 401)))

    await expect(getSession()).rejects.toBeInstanceOf(NotSignedInError)
  })

  it('throws SessionUnavailableError when the service fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(null, 503)))

    await expect(getSession()).rejects.toBeInstanceOf(SessionUnavailableError)
  })

  it('does not cache a failure', async () => {
    // An early failure would otherwise poison every write for the life of the page. This is the
    // difference between a transient blip and a session that never recovers without a reload.
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(null, 503))
      .mockResolvedValueOnce(jsonResponse(VALID_BODY))
    vi.stubGlobal('fetch', fetchMock)

    await expect(getSession()).rejects.toBeInstanceOf(SessionUnavailableError)
    await expect(getCsrfToken()).resolves.toBe('a-real-token')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it.each([
    ['missing csrf_token', { ...VALID_BODY, csrf_token: undefined }],
    ['empty csrf_token', { ...VALID_BODY, csrf_token: '' }],
    ['roles not an array', { ...VALID_BODY, roles: 'Secretariat' }],
    ['not an object', 'a string'],
    ['null', null],
  ])('refuses a malformed session body: %s', async (_label, body) => {
    // An empty token would build a request the server refuses in `compare_digest`, for a reason
    // the caller cannot see. Failing here says what actually happened.
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(body)))

    await expect(getSession()).rejects.toBeInstanceOf(SessionUnavailableError)
  })
})
