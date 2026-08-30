import { afterEach, describe, expect, it, vi } from 'vitest'
import { CommsDraftError, deleteCommsDraft, requestCommsDraft } from './client'
import { clearSession } from './session'

const DRAFT_ID = '00000000-0000-0000-0000-0000000000d1'

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
    const spy = mockFetch({ draft: 'Hello staff', id: DRAFT_ID, status: 'Draft' })
    const result = await requestCommsDraft({ contentType: 'newsletter', topic: 'Q3 update' })

    expect(result.draft).toBe('Hello staff')
    expect(result.id).toBe(DRAFT_ID)
    const [url, init] = draftCall(spy)
    expect(url).toBe('/api/comms/draft')
    expect(init.method).toBe('POST')
    expect(init.credentials).toBe('same-origin')
    // The full structured body (#303), not just the fields this call set. Empty key points and
    // links are sent as empty arrays rather than omitted, so the server sees the same shape every
    // time and a missing field always means a bug rather than "the user left it blank".
    expect(JSON.parse(init.body as string)).toEqual({
      content_type: 'newsletter',
      topic: 'Q3 update',
      key_points: [],
      links: [],
      tone: 'formal',
    })
  })

  it('trims and drops blank key points and links rather than sending them', async () => {
    // `id` and `status` are required by `isCommsDraftResult` since drafts became persisted rows;
    // a mock without them is rejected as an unrecognised response before the assertion is reached.
    const spy = mockFetch({ draft: 'x', id: DRAFT_ID, status: 'Draft' })
    await requestCommsDraft({
      contentType: 'newsletter',
      topic: 'Q3 update',
      keyPoints: ['  first  ', '   ', 'second'],
      links: ['', ' https://example.invalid/a '],
      tone: 'concise',
    })
    const body = JSON.parse(draftCall(spy)[1].body as string)
    expect(body.key_points).toEqual(['first', 'second'])
    expect(body.links).toEqual(['https://example.invalid/a'])
    expect(body.tone).toBe('concise')
  })

  it('honours a baseUrl for a cross-origin deployed shape', async () => {
    const spy = mockFetch({ draft: 'x', id: DRAFT_ID, status: 'Draft' })
    await requestCommsDraft({ contentType: 'linkedin_post', topic: 'x' }, { baseUrl: 'https://api.example.test' })
    expect(draftCall(spy)[0]).toBe('https://api.example.test/api/comms/draft')
  })

  it('raises a typed error when the service is unreachable, without inventing a draft', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')))
    await expect(requestCommsDraft({ contentType: 'newsletter', topic: 'x' })).rejects.toBeInstanceOf(
      CommsDraftError,
    )
  })

  it('raises a typed error on a non-ok response', async () => {
    mockFetch({}, { ok: false, status: 503 })
    await expect(requestCommsDraft({ contentType: 'newsletter', topic: 'x' })).rejects.toThrow('503')
  })

  it('propagates an abort rather than disguising it as a service error', async () => {
    const abort = new DOMException('aborted', 'AbortError')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abort))
    await expect(requestCommsDraft({ contentType: 'newsletter', topic: 'x' })).rejects.toBe(abort)
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
    await expect(requestCommsDraft({ contentType: 'newsletter', topic: 'x' })).rejects.toBeInstanceOf(
      CommsDraftError,
    )
  })

  it.each([
    ['a missing draft field', { id: DRAFT_ID, status: 'Draft' }],
    ['a non-string draft', { draft: 42, id: DRAFT_ID, status: 'Draft' }],
    ['an empty draft', { draft: '', id: DRAFT_ID, status: 'Draft' }],
    ['a non-object body', 'not json'],
    ['a missing id — additive fields the UI now relies on', { draft: 'x', status: 'Draft' }],
    ['an empty id', { draft: 'x', id: '', status: 'Draft' }],
    ['a missing status', { draft: 'x', id: DRAFT_ID }],
  ])('rejects %s', async (_label, body) => {
    mockFetch(body)
    await expect(requestCommsDraft({ contentType: 'newsletter', topic: 'x' })).rejects.toBeInstanceOf(
      CommsDraftError,
    )
  })
})

describe('CSRF', () => {
  it('sends the token from the session on the draft request', async () => {
    // The endpoint is behind `write_access`, which refuses a state-changing request with no
    // `X-CSRF-Token`. Sending the cookie alone is authenticated and refused, so without this the
    // draft button cannot work at all against the real API.
    const spy = mockFetch({ draft: 'Hello staff', id: DRAFT_ID, status: 'Draft' })

    await requestCommsDraft({ contentType: 'newsletter', topic: 'x' })

    const [, init] = draftCall(spy)
    expect((init.headers as Record<string, string>)['X-CSRF-Token']).toBe('a-real-token')
  })

  it('fetches the session before the draft, not after', async () => {
    clearSession()
    const spy = mockFetchWithSession({ draft: 'x', id: DRAFT_ID, status: 'Draft' })

    await requestCommsDraft({ contentType: 'newsletter', topic: 'x' })

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

    await expect(requestCommsDraft({ contentType: 'newsletter', topic: 'x' })).rejects.not.toBeInstanceOf(
      CommsDraftError,
    )
  })
})

describe('deleteCommsDraft', () => {
  it('sends DELETE with the reason in the body, same-origin, with the CSRF token', async () => {
    const spy = mockFetch(null, { status: 204 })

    await deleteCommsDraft(DRAFT_ID, 'contained personal information')

    const [url, init] = draftCall(spy)
    expect(url).toBe(`/api/comms/drafts/${DRAFT_ID}`)
    expect(init.method).toBe('DELETE')
    expect(init.credentials).toBe('same-origin')
    expect(JSON.parse(init.body as string)).toEqual({ reason: 'contained personal information' })
    expect((init.headers as Record<string, string>)['X-CSRF-Token']).toBe('a-real-token')
  })

  it('resolves with nothing on success', async () => {
    mockFetch(null, { status: 204 })
    await expect(deleteCommsDraft(DRAFT_ID, 'superseded')).resolves.toBeUndefined()
  })

  it('raises a distinct message on 404 — already gone, not a generic failure', async () => {
    mockFetch(null, { ok: false, status: 404 })
    await expect(deleteCommsDraft(DRAFT_ID, 'superseded')).rejects.toThrow(/no longer exists/i)
  })

  it('raises a distinct message on 403 — a real state, not a generic toast', async () => {
    mockFetch(null, { ok: false, status: 403 })
    await expect(deleteCommsDraft(DRAFT_ID, 'superseded')).rejects.toThrow(/permission/i)
  })

  it('raises a typed error when the service is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')))
    await expect(deleteCommsDraft(DRAFT_ID, 'superseded')).rejects.toBeInstanceOf(CommsDraftError)
  })

  it('propagates an abort rather than disguising it as a service error', async () => {
    const abort = new DOMException('aborted', 'AbortError')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abort))
    await expect(deleteCommsDraft(DRAFT_ID, 'superseded')).rejects.toBe(abort)
  })
})
