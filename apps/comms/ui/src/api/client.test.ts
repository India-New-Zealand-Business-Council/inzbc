import { afterEach, describe, expect, it, vi } from 'vitest'
import { CommsDraftError, requestCommsDraft } from './client'

function mockFetch(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  const { ok = true, status = 200 } = init
  const spy = vi.fn().mockResolvedValue({ ok, status, json: async () => body })
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => vi.unstubAllGlobals())

describe('requestCommsDraft', () => {
  it('posts the content type and brief, same-origin, and returns the draft', async () => {
    const spy = mockFetch({ draft: 'Hello staff' })
    const result = await requestCommsDraft({ contentType: 'newsletter', brief: 'Q3 update' })

    expect(result.draft).toBe('Hello staff')
    const call = spy.mock.calls[0]
    if (!call) throw new Error('fetch was not called')
    const [url, init] = call as [string, RequestInit]
    expect(url).toBe('/api/comms/draft')
    expect(init.method).toBe('POST')
    expect(init.credentials).toBe('same-origin')
    expect(JSON.parse(init.body as string)).toEqual({ content_type: 'newsletter', brief: 'Q3 update' })
  })

  it('honours a baseUrl for a cross-origin deployed shape', async () => {
    const spy = mockFetch({ draft: 'x' })
    await requestCommsDraft({ contentType: 'linkedin_post', brief: 'x' }, { baseUrl: 'https://api.example.test' })
    const call = spy.mock.calls[0]
    if (!call) throw new Error('fetch was not called')
    expect(call[0]).toBe('https://api.example.test/api/comms/draft')
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
