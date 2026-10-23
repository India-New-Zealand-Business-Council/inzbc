import { afterEach, describe, expect, it, vi } from 'vitest'
import { saveConfirmedSourceCheck } from './sourceLibraryClient'

afterEach(() => vi.unstubAllGlobals())

const confirmed = {
  source_id: 'src-1',
  outcome: 'Included' as const,
  fallback_used: false,
  notes: 'Analyst-confirmed evidence: internal://source-1',
}

describe('saveConfirmedSourceCheck', () => {
  it('sends an authenticated CSRF-protected POST for the selected run', async () => {
    const calls: Array<{ url: string; init: RequestInit }> = []
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url: String(url), init })
      if (String(url).includes('/api/session')) {
        return new Response(JSON.stringify({ csrf_token: 'csrf-test' }), { status: 200 })
      }
      return new Response(JSON.stringify({
        id: 'check-1', run_id: 'run 1', source_id: 'src-1', outcome: 'Included',
        checked_at: '2026-10-23T00:00:00Z', method: null,
        fallback_used: false, access_error: null, notes: confirmed.notes,
      }), { status: 201 })
    }))
    const result = await saveConfirmedSourceCheck('run 1', confirmed)
    const post = calls.find((call) => call.init.method === 'POST')
    expect(post?.url).toBe('/api/runs/run%201/source-checks')
    expect(post?.init.credentials).toBe('include')
    expect(post?.init.headers).toMatchObject({ 'Content-Type': 'application/json', 'X-CSRF-Token': 'csrf-test' })
    expect(JSON.parse(String(post?.init.body))).toMatchObject({ source_id: 'src-1', outcome: 'Included' })
    expect(result.run_id).toBe('run 1')
  })

  it('rejects incomplete evidence without issuing a request', async () => {
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    await expect(saveConfirmedSourceCheck('', confirmed)).rejects.toThrow(/select a run/i)
    await expect(saveConfirmedSourceCheck('run-1', { ...confirmed, source_id: '' })).rejects.toThrow(/source-library/i)
    await expect(saveConfirmedSourceCheck('run-1', { ...confirmed, notes: '' })).rejects.toThrow(/evidence/i)
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('preserves server authorization failures as a hard failure', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (String(url).includes('/api/session')) {
        return new Response(JSON.stringify({ csrf_token: 't' }), { status: 200 })
      }
      return new Response(JSON.stringify({ error: { status: 403, code: 'forbidden', message: 'Analyst role required' } }), { status: 403 })
    }))
    await expect(saveConfirmedSourceCheck('run-1', confirmed)).rejects.toMatchObject({ status: 403 })
  })
})
