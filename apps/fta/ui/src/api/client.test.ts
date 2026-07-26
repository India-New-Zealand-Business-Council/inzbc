import { readFileSync } from 'node:fs'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { escalation, woolAnswer } from '../components/fixtures'
import { FtaQueryError, REQUIRED_FIELDS, queryFta } from './client'

// Complete fixtures on purpose. Earlier versions of these tests passed partial objects, which
// meant they would have kept passing against a validator that never checked the fields.
const matched = {
  status: 'matched',
  query: 'wool',
  answers: [woolAnswer],
  action_required: null,
}
const noMatch = {
  status: 'no_match',
  query: 'zzzz',
  answers: [],
  action_required: escalation,
}

/** First URL the mocked fetch was called with. Narrowed because noUncheckedIndexedAccess is on. */
function calledUrl(spy: ReturnType<typeof vi.fn>): string {
  const call = spy.mock.calls[0]
  if (!call) throw new Error('fetch was not called')
  return String(call[0])
}

function mockFetch(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  const { ok = true, status = 200 } = init
  const spy = vi.fn().mockResolvedValue({ ok, status, json: async () => body })
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => vi.unstubAllGlobals())

describe('queryFta', () => {
  it('returns a matched envelope', async () => {
    mockFetch(matched)
    const result = await queryFta('wool')
    expect(result.status).toBe('matched')
    expect(result.answers).toHaveLength(1)
  })

  it('returns a no-match envelope with the escalation path', async () => {
    mockFetch(noMatch)
    const result = await queryFta('zzzz')
    expect(result.status).toBe('no_match')
    expect(result.answers).toEqual([])
    if (result.status === 'no_match') {
      expect(result.action_required?.escalation_path).toContain('INZBC')
    }
  })

  it('encodes the query so a URL-unsafe term cannot break the request', async () => {
    const spy = mockFetch(noMatch)
    await queryFta('dairy & wine?')
    expect(calledUrl(spy)).toBe('/api/fta/query?q=dairy%20%26%20wine%3F')
  })

  it('honours a baseUrl for the cross-origin deployed shape', async () => {
    const spy = mockFetch(matched)
    await queryFta('wool', { baseUrl: 'https://api.example.test' })
    expect(calledUrl(spy)).toBe('https://api.example.test/api/fta/query?q=wool')
  })

  it('raises a typed error when the service is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')))
    await expect(queryFta('wool')).rejects.toBeInstanceOf(FtaQueryError)
  })

  it('raises a typed error on a non-200 response', async () => {
    mockFetch({}, { ok: false, status: 503 })
    await expect(queryFta('wool')).rejects.toThrow('503')
  })

  it('propagates an abort rather than disguising it as a service error', async () => {
    const abort = new DOMException('aborted', 'AbortError')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abort))
    await expect(queryFta('wool')).rejects.toBe(abort)
  })

  it.each([
    ['matched with no answers', { status: 'matched', query: 'q', answers: [], action_required: null }],
    ['matched that also escalates', { status: 'matched', query: 'q', answers: [woolAnswer], action_required: escalation }],
    ['no_match carrying answers', { status: 'no_match', query: 'q', answers: [woolAnswer], action_required: escalation }],
    ['no_match with no escalation', { status: 'no_match', query: 'q', answers: [], action_required: null }],
    ['an unknown status', { status: 'partial', query: 'q', answers: [] }],
    ['a non-object body', 'not json'],
    ['a missing query field', { status: 'no_match', answers: [], action_required: escalation }],
    // The case the previous shallow guard accepted.
    ['an answer with no evidence fields', { status: 'matched', query: 'q', answers: [{}], action_required: null }],
    ['an answer missing only its citation', {
      status: 'matched', query: 'q', action_required: null,
      answers: [{ ...woolAnswer, citation: undefined }],
    }],
    ['an answer with an empty citation', {
      status: 'matched', query: 'q', action_required: null,
      answers: [{ ...woolAnswer, citation: '' }],
    }],
    ['an escalation missing its path', {
      status: 'no_match', query: 'q', answers: [],
      action_required: { ...escalation, escalation_path: undefined },
    }],
  ])('rejects %s', async (_label, body) => {
    mockFetch(body)
    await expect(queryFta('q')).rejects.toBeInstanceOf(FtaQueryError)
  })
})


describe('runtime validation matches the published contract', () => {
  // Without this, the hand-maintained required-field lists are a second source of truth that
  // can drift from the API. Reading the schema keeps them honest.
  const schema = JSON.parse(readFileSync('../../../schemas/openapi.json', 'utf8')) as {
    components: { schemas: Record<string, { required?: string[] }> }
  }

  it.each(['AnswerOut', 'ActionRequiredOut'] as const)(
    "%s's required fields match schemas/openapi.json",
    (name) => {
      const fromSchema = [...(schema.components.schemas[name]?.required ?? [])].sort()
      const fromClient = [...REQUIRED_FIELDS[name]].sort()
      expect(fromClient).toEqual(fromSchema)
    },
  )
})
