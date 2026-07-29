import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CommsAssistant } from './CommsAssistant'

function mockFetch(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  const { ok = true, status = 200 } = init
  const spy = vi.fn().mockResolvedValue({ ok, status, json: async () => body })
  vi.stubGlobal('fetch', spy)
  return spy
}

function stubClipboard(writeText: ReturnType<typeof vi.fn>) {
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText },
    configurable: true,
  })
}

afterEach(() => vi.unstubAllGlobals())

describe('CommsAssistant', () => {
  it('disables submit until a brief is entered, and never submits whitespace only', async () => {
    const spy = mockFetch({ draft: 'x' })
    render(<CommsAssistant />)
    expect(screen.getByRole('button', { name: /generate draft/i })).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/brief/i), '   ')
    expect(screen.getByRole('button', { name: /generate draft/i })).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/brief/i), 'Announce the trade mission');
    expect(screen.getByRole('button', { name: /generate draft/i })).toBeEnabled()
    expect(spy).not.toHaveBeenCalled()
  })

  it('submits the selected content type and brief, then renders the draft', async () => {
    const spy = mockFetch({ draft: 'Draft newsletter body' })
    render(<CommsAssistant />)

    await userEvent.selectOptions(screen.getByLabelText(/content type/i), 'LinkedIn Post')
    await userEvent.type(screen.getByLabelText(/brief/i), 'Celebrate the FTA anniversary')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))

    expect(await screen.findByText('Draft newsletter body')).toBeInTheDocument()
    const call = spy.mock.calls[0]
    if (!call) throw new Error('fetch was not called')
    const [, init] = call as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toMatchObject({ content_type: 'linkedin_post' })
  })

  it('shows a loading state while waiting for the response', async () => {
    let resolveFetch: (value: unknown) => void = () => {}
    vi.stubGlobal(
      'fetch',
      vi.fn().mockReturnValue(
        new Promise((resolve) => {
          resolveFetch = resolve
        }),
      ),
    )
    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))

    expect(screen.getByRole('button', { name: /generating/i })).toBeDisabled()
    resolveFetch({ ok: true, status: 200, json: async () => ({ draft: 'done' }) })
    expect(await screen.findByText('done')).toBeInTheDocument()
  })

  it('surfaces a service failure without inventing a draft', async () => {
    mockFetch({}, { ok: false, status: 503 })
    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/503/)
    expect(screen.queryByRole('heading', { name: /draft/i })).not.toBeInTheDocument()
  })

  it('copies the rendered draft to the clipboard', async () => {
    mockFetch({ draft: 'Copy me' })
    const writeText = vi.fn().mockResolvedValue(undefined)
    stubClipboard(writeText)

    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Copy me')
    await userEvent.click(screen.getByRole('button', { name: /copy to clipboard/i }))

    expect(writeText).toHaveBeenCalledWith('Copy me')
    expect(await screen.findByRole('button', { name: /^copied$/i })).toBeInTheDocument()
  })

  it('shows a copy-failed state when the clipboard write rejects', async () => {
    mockFetch({ draft: 'Copy me' })
    stubClipboard(vi.fn().mockRejectedValue(new Error('denied')))

    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Copy me')
    await userEvent.click(screen.getByRole('button', { name: /copy to clipboard/i }))

    expect(await screen.findByRole('button', { name: /copy failed/i })).toBeInTheDocument()
  })

  it('clears the brief, content type, and any rendered draft on reset', async () => {
    mockFetch({ draft: 'Copy me' })
    render(<CommsAssistant />)

    await userEvent.selectOptions(screen.getByLabelText(/content type/i), 'LinkedIn Post')
    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Copy me')

    await userEvent.click(screen.getByRole('button', { name: /^clear$/i }))

    expect(screen.getByLabelText(/brief/i)).toHaveValue('')
    expect(screen.getByLabelText(/content type/i)).toHaveValue('newsletter')
    expect(screen.queryByText('Copy me')).not.toBeInTheDocument()
  })

  it('abandons an in-flight request when a second submit starts', async () => {
    const aborts: AbortSignal[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_url, init: RequestInit) => {
        if (init.signal) aborts.push(init.signal)
        return new Promise((resolve) =>
          setTimeout(() => resolve({ ok: true, status: 200, json: async () => ({ draft: 'late' }) }), 5),
        )
      }),
    )
    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    // Same accessible-name trick as apps/fta/ui's FtaQuery test: "Generat" matches both the
    // enabled "Generate draft" label and the disabled "Generating…" label, so this fires two
    // submits back to back regardless of exactly when the disabled state commits.
    await userEvent.click(screen.getByRole('button', { name: /generat/i }))
    await userEvent.click(screen.getByRole('button', { name: /generat/i }))

    await waitFor(() => expect(aborts.length).toBeGreaterThan(1))
    expect(aborts[0]?.aborted).toBe(true)
  })

  it('states plainly that outputs are drafts only', () => {
    render(<CommsAssistant />)
    expect(screen.getByText(/drafts only/i)).toBeInTheDocument()
  })

  it('shows a live character count against the brief limit', async () => {
    render(<CommsAssistant />)
    expect(screen.getByText('0 / 4000')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    expect(screen.getByText('10 / 4000')).toBeInTheDocument()
  })
})
