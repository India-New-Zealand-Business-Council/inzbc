import { afterEach, describe, expect, it, vi } from 'vitest'
import { CommsDraftError, requestCommsDraft } from './client'
import { clearSession } from './session'

const SESSION_BODY = {
  user_id: '00000000-0000-0000-0000-0000000000aa',
  name: 'Test Principal',
  roles: ['Secretariat'],
  csrf_token: 'a-real-token',
}

/**
 * `vitest.setup.ts` seeds a session for every test, so the draft is the only request the client
 * makes here and this mock stays as simple as it was. The tests that exercise the session fetch
 * itself clear the seed first, and say so.
 */
function mockFetch(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  const { ok = true, status = 200 } = init
  const spy = vi.fn().mockResolvedValue({ ok, status, json: async () => body })
  vi.stubGlobal('fetch', spy)
  return spy
}

/** Serves the session, then everything else. For the tests that clear the seeded session. */
function mockFetchWithSession(body: unknown) {
  const spy = vi.fn(async (url: string) =>
    url.endsWith('/api/session')
      ? { ok: true, status: 200, json: async () => SESSION_BODY }
      : { ok: true, status: 200, json: async () => body },
  )
  vi.stubGlobal('fetch', spy)
  return spy
}

function draftCall(spy: { mock: { calls: unknown[][] } }): [string, RequestInit] {
  const call = spy.mock.calls.find((c) => !String(c[0]).endsWith('/api/session'))
  if (!call) throw new Error('the draft request was not made')
  return call as [string, RequestInit]
}

afterEach(() => vi.unstubAllGlobals())

describe('requestCommsDraft', () => {
  it('posts the content type and brief, same-origin, and returns the draft', async () => {
    const spy = mockFetch({ draft: 'Hello staff' })
    const result = await requestCommsDraft({ contentType: 'newsletter', brief: 'Q3 update' })

    expect(result.draft).toBe('Hello staff')
    const [url, init] = draftCall(spy)
    expect(url).toBe('/api/comms/draft')
    expect(init.method).toBe('POST')
    expect(init.credentials).toBe('same-origin')
    expect(JSON.parse(init.body as string)).toEqual({ content_type: 'newsletter', brief: 'Q3 update' })
  })

  it('honours a baseUrl for a cross-origin deployed shape', async () => {
    const spy = mockFetch({ draft: 'x' })
    await requestCommsDraft({ contentType: 'linkedin_post', brief: 'x' }, { baseUrl: 'https://api.example.test' })
    expect(draftCall(spy)[0]).toBe('https://api.example.test/api/comms/draft')
  })

  it('raises a typed error when the service is unreachable, without inventing a draft', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')))
    await expect(requestCommsDraft({ contentType: 'newsletter', brief: 'x' })).rejects.toBeInstanceOf(
      CommsDraftError,
    )
  })

  it('raises a typed error on a non-ok response', async () => {
    mockFetch({}, { ok: false, status: 503 })
    await expect(requestCommsDraft({ contentType: 'newsletter', brief: 'x' })).rejects.toThrow('503')
  })

  it('propagates an abort rather than disguising it as a service error', async () => {
    const abort = new DOMException('aborted', 'AbortError')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abort))
    await expect(requestCommsDraft({ contentType: 'newsletter', brief: 'x' })).rejects.toBe(abort)
  })

  it('raises a typed error when the response body cannot be parsed as JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => {
          throw new SyntaxError('bad json')
        },
      }),
    )
    await expect(requestCommsDraft({ contentType: 'newsletter', brief: 'x' })).rejects.toBeInstanceOf(
      CommsDraftError,
    )
  })

  it.each([
    ['a missing draft field', {}],
    ['a non-string draft', { draft: 42 }],
    ['an empty draft', { draft: '' }],
    ['a non-object body', 'not json'],
  ])('rejects %s', async (_label, body) => {
    mockFetch(body)
    await expect(requestCommsDraft({ contentType: 'newsletter', brief: 'x' })).rejects.toBeInstanceOf(
      CommsDraftError,
    )
  })
})

describe('CSRF', () => {
  it('sends the token from the session on the draft request', async () => {
    // The endpoint is behind `write_access`, which refuses a state-changing request with no
    // `X-CSRF-Token`. Sending the cookie alone is authenticated and refused, so without this the
    // draft button cannot work at all against the real API.
    const spy = mockFetch({ draft: 'Hello staff' })

    await requestCommsDraft({ contentType: 'newsletter', brief: 'x' })

    const [, init] = draftCall(spy)
    expect((init.headers as Record<string, string>)['X-CSRF-Token']).toBe('a-real-token')
  })

  it('fetches the session before the draft, not after', async () => {
    clearSession()
    const spy = mockFetchWithSession({ draft: 'x' })

    await requestCommsDraft({ contentType: 'newsletter', brief: 'x' })

    expect(spy.mock.calls[0]?.[0]).toBe('/api/session')
    expect(spy.mock.calls[1]?.[0]).toBe('/api/comms/draft')
  })

  it('does not send a draft when there is no session', async () => {
    clearSession()
    // A caller that is not signed in must not have its brief sent anywhere. The failure is the
    // session, and the message should say so rather than reporting a drafting failure.
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, status: 401, json: async () => null })),
    )

    await expect(requestCommsDraft({ contentType: 'newsletter', brief: 'x' })).rejects.not.toBeInstanceOf(
      CommsDraftError,
    )
  })
})
