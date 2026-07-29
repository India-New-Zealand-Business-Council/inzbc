import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as exportDraft from '../lib/exportDraft'
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

  it('shows a loading skeleton while generating, gone once the draft renders', async () => {
    let resolveFetch: (value: unknown) => void = () => {}
    vi.stubGlobal(
      'fetch',
      vi.fn().mockReturnValue(
        new Promise((resolve) => {
          resolveFetch = resolve
        }),
      ),
    )
    const { container } = render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))

    expect(container.querySelector('[aria-hidden="true"] .animate-pulse')).toBeTruthy()
    resolveFetch({ ok: true, status: 200, json: async () => ({ draft: 'done' }) })
    await screen.findByText('done')
    expect(container.querySelector('[aria-hidden="true"] .animate-pulse')).toBeFalsy()
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

  it('shows a toast notification when the copy succeeds', async () => {
    mockFetch({ draft: 'Copy me' })
    stubClipboard(vi.fn().mockResolvedValue(undefined))

    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Copy me')
    expect(screen.queryByRole('status')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /copy to clipboard/i }))
    expect(await screen.findByRole('status')).toHaveTextContent(/copied to clipboard/i)
  })

  it('shows a toast notification when the copy fails', async () => {
    mockFetch({ draft: 'Copy me' })
    stubClipboard(vi.fn().mockRejectedValue(new Error('denied')))

    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Copy me')
    await userEvent.click(screen.getByRole('button', { name: /copy to clipboard/i }))

    expect(await screen.findByRole('status')).toHaveTextContent(/couldn.t copy to clipboard/i)
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

  it('carries the required human-review disclaimer', () => {
    render(<CommsAssistant />)
    expect(screen.getByText(/ai drafts require human review before publishing/i)).toBeInTheDocument()
  })

  it('shows a live character count against the brief limit', async () => {
    render(<CommsAssistant />)
    expect(screen.getByText('0 / 4000')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    expect(screen.getByText('10 / 4000')).toBeInTheDocument()
  })

  it('moves a superseded draft into recent-drafts history, keeping its content type', async () => {
    const spy = vi.fn()
    vi.stubGlobal(
      'fetch',
      spy.mockImplementation(async (_url: string, init: RequestInit) => {
        const { content_type: contentType } = JSON.parse(init.body as string) as { content_type: string }
        return { ok: true, status: 200, json: async () => ({ draft: `${contentType} draft` }) }
      }),
    )
    render(<CommsAssistant />)

    expect(screen.queryByText(/recent drafts/i)).not.toBeInTheDocument()

    await userEvent.type(screen.getByLabelText(/brief/i), 'First brief')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('newsletter draft')
    expect(screen.queryByText(/recent drafts/i)).not.toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText(/content type/i), 'LinkedIn Post')
    await userEvent.clear(screen.getByLabelText(/brief/i))
    await userEvent.type(screen.getByLabelText(/brief/i), 'Second brief')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('linkedin_post draft')

    expect(await screen.findByRole('heading', { name: /recent drafts/i })).toBeInTheDocument()
    expect(screen.getByText('Newsletter')).toBeInTheDocument()
    expect(screen.getByText('newsletter draft')).toBeInTheDocument()
  })

  it('keeps history capped at the 3 most recent superseded drafts', async () => {
    let counter = 0
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async () => {
        counter += 1
        return { ok: true, status: 200, json: async () => ({ draft: `draft ${counter}` }) }
      }),
    )
    render(<CommsAssistant />)

    for (let i = 0; i < 5; i += 1) {
      await userEvent.clear(screen.getByLabelText(/brief/i))
      await userEvent.type(screen.getByLabelText(/brief/i), `brief ${i}`)
      await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
      await screen.findByText(`draft ${i + 1}`)
    }

    // 5 generations supersede 4 drafts (draft 1..4); only the 3 most recent survive in history.
    expect(screen.queryByText('draft 1')).not.toBeInTheDocument()
    expect(screen.getByText('draft 2')).toBeInTheDocument()
    expect(screen.getByText('draft 3')).toBeInTheDocument()
    expect(screen.getByText('draft 4')).toBeInTheDocument()
  })

  it('exports the current draft to Word with its content type in the filename', async () => {
    mockFetch({ draft: 'Export me' })
    const downloadSpy = vi.spyOn(exportDraft, 'downloadAsWord').mockImplementation(() => {})

    render(<CommsAssistant />)
    await userEvent.selectOptions(screen.getByLabelText(/content type/i), 'LinkedIn Post')
    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Export me')

    await userEvent.click(screen.getByRole('button', { name: /export as word/i }))
    expect(downloadSpy).toHaveBeenCalledWith('Export me', 'linkedin_post-draft')
  })

  it('shows the word count of the generated draft', async () => {
    mockFetch({ draft: 'Four little words here' })
    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))

    expect(await screen.findByText(/4 words/i)).toBeInTheDocument()
  })

  it('submits the brief on Ctrl+Enter', async () => {
    const spy = mockFetch({ draft: 'From shortcut' })
    render(<CommsAssistant />)

    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this{Control>}{Enter}{/Control}')

    expect(await screen.findByText('From shortcut')).toBeInTheDocument()
    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('does not submit on plain Enter, so a brief can still span multiple lines', async () => {
    const spy = mockFetch({ draft: 'x' })
    render(<CommsAssistant />)

    await userEvent.type(screen.getByLabelText(/brief/i), 'Line one{Enter}Line two')

    expect(spy).not.toHaveBeenCalled()
    expect(screen.getByLabelText(/brief/i)).toHaveValue('Line one\nLine two')
  })

  it('exports the current draft to PDF via the print dialog', async () => {
    mockFetch({ draft: 'Export me' })
    const pdfSpy = vi.spyOn(exportDraft, 'exportAsPdf').mockImplementation(() => {})

    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/brief/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Export me')

    await userEvent.click(screen.getByRole('button', { name: /export as pdf/i }))
    expect(pdfSpy).toHaveBeenCalledTimes(1)
  })
})
