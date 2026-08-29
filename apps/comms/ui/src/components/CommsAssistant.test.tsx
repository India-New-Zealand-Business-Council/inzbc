import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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
  it('disables submit until a brief is entered', async () => {
    render(<CommsAssistant />)
    expect(screen.getByRole('button', { name: /generate draft/i })).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/topic/i), '   ')
    expect(screen.getByRole('button', { name: /generate draft/i })).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/topic/i), 'Announce the trade mission')
    expect(screen.getByRole('button', { name: /generate draft/i })).toBeEnabled()
  })

  it('never submits whitespace only, even via the Ctrl+Enter shortcut that bypasses the disabled button', async () => {
    // The button-disabled test above never attempts a submission, so it can't catch a broken
    // whitespace guard inside generateDraft() itself — only Ctrl+Enter (onBriefKeyDown) calls
    // generateDraft() directly, independent of the button's disabled attribute.
    const spy = mockFetch({ draft: 'x' })
    render(<CommsAssistant />)

    await userEvent.type(screen.getByLabelText(/topic/i), '   {Control>}{Enter}{/Control}')

    expect(spy).not.toHaveBeenCalled()
  })

  it('submits the selected content type and brief, then renders the draft', async () => {
    const spy = mockFetch({ draft: 'Draft newsletter body' })
    render(<CommsAssistant />)

    await userEvent.selectOptions(screen.getByLabelText(/content type/i), 'LinkedIn Post')
    await userEvent.type(screen.getByLabelText(/topic/i), 'Celebrate the FTA anniversary')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))

    expect(await screen.findByText('Draft newsletter body')).toBeInTheDocument()
    const call = spy.mock.calls[0]
    if (!call) throw new Error('fetch was not called')
    const [, init] = call as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toMatchObject({
      content_type: 'linkedin_post',
      topic: 'Celebrate the FTA anniversary',
    })
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
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
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
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))

    expect(container.querySelector('[aria-hidden="true"] .animate-pulse')).toBeTruthy()
    resolveFetch({ ok: true, status: 200, json: async () => ({ draft: 'done' }) })
    await screen.findByText('done')
    expect(container.querySelector('[aria-hidden="true"] .animate-pulse')).toBeFalsy()
  })

  it('surfaces a service failure without inventing a draft', async () => {
    mockFetch({}, { ok: false, status: 503 })
    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/503/)
    expect(screen.queryByRole('heading', { name: /draft/i })).not.toBeInTheDocument()
  })

  it('keeps the previous draft visible when a regeneration fails', async () => {
    // A failed *second* generateDraft() call used to wipe the already-rendered draft along with
    // it: generate A, ask for a revision, hit a 503, A is gone with no recovery. draftState must
    // stay untouched on a failed regeneration; only submitError should change.
    mockFetch({ draft: 'First draft' })
    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('First draft')

    mockFetch({}, { ok: false, status: 503 })
    await userEvent.clear(screen.getByLabelText(/topic/i))
    await userEvent.type(screen.getByLabelText(/topic/i), 'Revise this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/503/)
    expect(screen.getByText('First draft')).toBeInTheDocument()
  })

  it('copies the rendered draft to the clipboard', async () => {
    mockFetch({ draft: 'Copy me' })
    const writeText = vi.fn().mockResolvedValue(undefined)
    stubClipboard(writeText)

    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
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
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Copy me')
    await userEvent.click(screen.getByRole('button', { name: /copy to clipboard/i }))

    expect(await screen.findByRole('button', { name: /copy failed/i })).toBeInTheDocument()
  })

  it('shows a toast notification when the copy succeeds', async () => {
    mockFetch({ draft: 'Copy me' })
    stubClipboard(vi.fn().mockResolvedValue(undefined))

    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Copy me')
    expect(screen.queryByRole('status')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /copy to clipboard/i }))
    const toast = await screen.findByRole('status')
    expect(toast).toHaveTextContent(/copied to clipboard/i)
    // inset-x-4 keeps the toast within a 320px viewport instead of overflowing off a fixed
    // right-anchored position (WCAG 2.2 §1.4.10 reflow).
    expect(toast.className).toContain('inset-x-4')
  })

  it('shows a toast notification when the copy fails', async () => {
    mockFetch({ draft: 'Copy me' })
    stubClipboard(vi.fn().mockRejectedValue(new Error('denied')))

    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Copy me')
    await userEvent.click(screen.getByRole('button', { name: /copy to clipboard/i }))

    expect(await screen.findByRole('status')).toHaveTextContent(/couldn.t copy to clipboard/i)
  })

  it('clears the brief, content type, and any rendered draft on reset', async () => {
    mockFetch({ draft: 'Copy me' })
    render(<CommsAssistant />)

    await userEvent.selectOptions(screen.getByLabelText(/content type/i), 'LinkedIn Post')
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Copy me')

    await userEvent.click(screen.getByRole('button', { name: /^clear$/i }))

    expect(screen.getByLabelText(/topic/i)).toHaveValue('')
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
    const textarea = screen.getByLabelText(/topic/i)
    await userEvent.type(textarea, 'Draft this')
    // Two Ctrl+Enter keydowns fired without an await between them, not two button clicks: the
    // button disables after the first submit starts, so userEvent.click's second call may or may
    // not register a click depending on exactly when React commits that disabled state — a race,
    // not a guarantee. fireEvent.keyDown calls onBriefKeyDown (and so generateDraft()) directly
    // and synchronously, independent of the button's disabled attribute, so both requests are
    // guaranteed to start before either resolves.
    fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true })
    fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true })

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

  it('shows a live character count against the topic limit', async () => {
    // 200, not the old 4000: #303 replaced one free-text box with capped fields, and the cap is
    // the mitigation, so the counter has to show the real one.
    render(<CommsAssistant />)
    expect(screen.getByText('0 / 200')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
    expect(screen.getByText('10 / 200')).toBeInTheDocument()
  })

  it('counts key points and links against their own limits', async () => {
    render(<CommsAssistant />)
    expect(screen.getByText('0 / 8')).toBeInTheDocument()
    expect(screen.getByText('0 / 5')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText(/key points/i), 'one\ntwo')
    expect(screen.getByText('2 / 8')).toBeInTheDocument()
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

    await userEvent.type(screen.getByLabelText(/topic/i), 'First brief')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('newsletter draft')
    expect(screen.queryByText(/recent drafts/i)).not.toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText(/content type/i), 'LinkedIn Post')
    await userEvent.clear(screen.getByLabelText(/topic/i))
    await userEvent.type(screen.getByLabelText(/topic/i), 'Second brief')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('linkedin_post draft')

    const heading = await screen.findByRole('heading', { name: /recent drafts/i })
    // Scoped to the history region: bare getByText('Newsletter') also matches the still-present
    // <option> in the content-type select, so it found two nodes and threw.
    const historyRegion = within(heading.parentElement as HTMLElement)
    expect(historyRegion.getByText('Newsletter')).toBeInTheDocument()
    expect(historyRegion.getByText('newsletter draft')).toBeInTheDocument()
  })

  it('clears history when the draft is cleared', async () => {
    // Clear used to leave prior drafts on screen. Once /api/comms/draft exists these carry real
    // briefs, so Clear has to mean cleared.
    let counter = 0
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async () => {
        counter += 1
        return { ok: true, status: 200, json: async () => ({ draft: `draft ${counter}` }) }
      }),
    )
    render(<CommsAssistant />)

    for (let i = 0; i < 2; i += 1) {
      await userEvent.clear(screen.getByLabelText(/topic/i))
      await userEvent.type(screen.getByLabelText(/topic/i), `brief ${i}`)
      await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
      await screen.findByText(`draft ${i + 1}`)
    }
    expect(await screen.findByRole('heading', { name: /recent drafts/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /^clear$/i }))

    expect(screen.queryByRole('heading', { name: /recent drafts/i })).not.toBeInTheDocument()
    expect(screen.queryByText('draft 1')).not.toBeInTheDocument()
    expect(screen.queryByText('draft 2')).not.toBeInTheDocument()
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
      await userEvent.clear(screen.getByLabelText(/topic/i))
      await userEvent.type(screen.getByLabelText(/topic/i), `brief ${i}`)
      await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
      await screen.findByText(`draft ${i + 1}`)
    }

    // 5 generations supersede 4 drafts (draft 1..4); only the 3 most recent survive in history.
    expect(screen.queryByText('draft 1')).not.toBeInTheDocument()
    expect(screen.getByText('draft 2')).toBeInTheDocument()
    expect(screen.getByText('draft 3')).toBeInTheDocument()
    expect(screen.getByText('draft 4')).toBeInTheDocument()
  })

  it('toggles thumbs-up/thumbs-down feedback on the draft', async () => {
    mockFetch({ draft: 'Rate me' })
    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Rate me')

    const up = screen.getByRole('button', { name: 'Helpful' })
    const down = screen.getByRole('button', { name: 'Not helpful' })
    expect(up).toHaveAttribute('aria-pressed', 'false')
    expect(down).toHaveAttribute('aria-pressed', 'false')

    await userEvent.click(up)
    expect(up).toHaveAttribute('aria-pressed', 'true')
    expect(down).toHaveAttribute('aria-pressed', 'false')

    // Clicking the same choice again clears it, rather than being a one-way ratchet.
    await userEvent.click(up)
    expect(up).toHaveAttribute('aria-pressed', 'false')
  })

  it('resets feedback when a new draft is generated', async () => {
    mockFetch({ draft: 'First' })
    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('First')
    await userEvent.click(screen.getByRole('button', { name: 'Helpful' }))
    expect(screen.getByRole('button', { name: 'Helpful' })).toHaveAttribute('aria-pressed', 'true')

    mockFetch({ draft: 'Second' })
    await userEvent.clear(screen.getByLabelText(/topic/i))
    await userEvent.type(screen.getByLabelText(/topic/i), 'Another brief')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Second')

    expect(screen.getByRole('button', { name: 'Helpful' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('exports the current draft to Word with its content type in the filename', async () => {
    mockFetch({ draft: 'Export me' })
    const downloadSpy = vi.spyOn(exportDraft, 'downloadAsWord').mockImplementation(() => {})

    render(<CommsAssistant />)
    await userEvent.selectOptions(screen.getByLabelText(/content type/i), 'LinkedIn Post')
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Export me')

    await userEvent.click(screen.getByRole('button', { name: /export as word/i }))
    expect(downloadSpy).toHaveBeenCalledWith('Export me', 'linkedin_post-draft')
  })

  it('shows the word count of the generated draft', async () => {
    mockFetch({ draft: 'Four little words here' })
    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))

    expect(await screen.findByText(/4 words/i)).toBeInTheDocument()
  })

  it('submits the brief on Ctrl+Enter', async () => {
    const spy = mockFetch({ draft: 'From shortcut' })
    render(<CommsAssistant />)

    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this{Control>}{Enter}{/Control}')

    expect(await screen.findByText('From shortcut')).toBeInTheDocument()
    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('cancels plain Enter in the topic field so the form cannot submit', async () => {
    // Topic became a single-line input in #303, and an input inside a form submits on Enter
    // natively. Ctrl+Enter stays the only submit shortcut.
    //
    // Asserts the event was cancelled rather than asserting "fetch was not called". jsdom does not
    // implement implicit form submission, so a not-called assertion passes whether or not the
    // guard exists - it did exactly that when the guard was removed, and reported success.
    // fireEvent returns false when preventDefault was called, which tests the guard itself.
    const spy = mockFetch({ draft: 'x' })
    render(<CommsAssistant />)

    const topic = screen.getByLabelText(/topic/i)
    await userEvent.type(topic, 'Line one')

    const notCancelled = fireEvent.keyDown(topic, { key: 'Enter' })
    expect(notCancelled).toBe(false)
    expect(spy).not.toHaveBeenCalled()
  })

  it('blocks submit and says why when a field is over its cap', async () => {
    // Adversarial review found the counters turned red while submit stayed enabled, so the only
    // feedback was a bare "returned 422" from the server. The rules here mirror the server's.
    const spy = mockFetch({ draft: 'x' })
    render(<CommsAssistant />)

    await userEvent.type(screen.getByLabelText(/topic/i), 'A topic')
    expect(screen.getByRole('button', { name: /generate/i })).toBeEnabled()

    // Nine key points against a limit of eight.
    fireEvent.change(screen.getByLabelText(/key points/i), {
      target: { value: Array.from({ length: 9 }, (_, i) => `point ${i}`).join('\n') },
    })

    expect(screen.getByRole('button', { name: /generate/i })).toBeDisabled()
    expect(screen.getByRole('alert')).toHaveTextContent(/no more than 8 key points/i)
    expect(spy).not.toHaveBeenCalled()
  })

  it('requires a topic, because the server does', async () => {
    // canSubmit previously allowed a key-points-only brief while DraftIn.topic has min_length=1,
    // so that combination was a guaranteed 422.
    render(<CommsAssistant />)
    fireEvent.change(screen.getByLabelText(/key points/i), { target: { value: 'a real point' } })
    expect(screen.getByRole('button', { name: /generate/i })).toBeDisabled()
  })

  it('clearing during generation does not leave the form stuck', async () => {
    // Abort skips the catch block that would normally clear isGenerating, so Clear mid-request
    // used to brick the form until reload.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise(() => {})),
    )
    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/topic/i), 'A topic')
    await userEvent.click(screen.getByRole('button', { name: /generate/i }))
    await userEvent.click(screen.getByRole('button', { name: /clear/i }))

    await userEvent.type(screen.getByLabelText(/topic/i), 'Another topic')
    expect(screen.getByRole('button', { name: /generate/i })).toBeEnabled()
  })

  it('announces the external-model warning from every brief field', () => {
    // The warning sat under key points alone, so it was absent from Topic and Links — the two
    // fields the code itself names as the residual #303 risk. Every field now references it, and
    // aria-describedby is what makes that true for a screen reader rather than only visually.
    render(<CommsAssistant />)

    const warning = screen.getByText(/do not enter member names/i)
    for (const label of [/topic/i, /key points/i, /links/i]) {
      const described = screen.getByLabelText(label).getAttribute('aria-describedby') ?? ''
      expect(described.split(' ')).toContain(warning.id)
    }
  })

  it('associates each counter with its field', () => {
    render(<CommsAssistant />)
    for (const label of [/topic/i, /key points/i, /links/i]) {
      const described = screen.getByLabelText(label).getAttribute('aria-describedby') ?? ''
      // At least one referenced id must exist in the document, or the attribute is decorative.
      expect(described.split(' ').some((id) => document.getElementById(id) !== null)).toBe(true)
    }
  })

  it('leaves plain Enter alone in the key points textarea', async () => {
    // The mirror of the test above: the guard must be narrow. Cancelling Enter in a textarea
    // would stop key points being more than one line, which is the whole point of that field.
    render(<CommsAssistant />)
    const keyPoints = screen.getByLabelText(/key points/i)
    const notCancelled = fireEvent.keyDown(keyPoints, { key: 'Enter' })
    expect(notCancelled).toBe(true)
  })

  it('keeps plain Enter as a newline in key points, so a list can span lines', async () => {
    const spy = mockFetch({ draft: 'x' })
    render(<CommsAssistant />)

    await userEvent.type(screen.getByLabelText(/key points/i), 'Line one{Enter}Line two')

    expect(spy).not.toHaveBeenCalled()
    expect(screen.getByLabelText(/key points/i)).toHaveValue('Line one\nLine two')
  })

  it('exports the current draft to PDF via the print dialog', async () => {
    mockFetch({ draft: 'Export me' })
    const pdfSpy = vi.spyOn(exportDraft, 'exportAsPdf').mockImplementation(() => {})

    render(<CommsAssistant />)
    await userEvent.type(screen.getByLabelText(/topic/i), 'Draft this')
    await userEvent.click(screen.getByRole('button', { name: /generate draft/i }))
    await screen.findByText('Export me')

    await userEvent.click(screen.getByRole('button', { name: /export as pdf/i }))
    expect(pdfSpy).toHaveBeenCalledTimes(1)
  })
})
