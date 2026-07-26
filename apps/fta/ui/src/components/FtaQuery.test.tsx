import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FtaQuery } from './FtaQuery'
import { escalation, woolAnswer } from './fixtures'

function mockJson(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  const { ok = true, status = 200 } = init
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok, status, json: async () => body }))
}

const matched = { status: 'matched', query: 'wool', answers: [woolAnswer], action_required: null }
const noMatch = { status: 'no_match', query: 'zzzz', answers: [], action_required: escalation }

afterEach(() => vi.unstubAllGlobals())

describe('FtaQuery', () => {
  it('renders a sourced answer with its citation, confidence and disclaimer', async () => {
    mockJson(matched)
    render(<FtaQuery />)
    await userEvent.type(screen.getByLabelText(/ask about the nz–india fta/i), 'wool')
    await userEvent.click(screen.getByRole('button', { name: /search/i }))

    expect(await screen.findByRole('heading', { name: 'Wool' })).toBeInTheDocument()
    expect(screen.getByText(/MFAT National Interest Analysis/)).toBeInTheDocument()
    expect(screen.getByText(/official government or treaty sources/)).toBeInTheDocument()
    expect(screen.getByText(/indicate this rather than speculate/)).toBeInTheDocument()
  })

  it('renders the escalation state for a no-match, not an empty result list', async () => {
    mockJson(noMatch)
    render(<FtaQuery />)
    await userEvent.type(screen.getByLabelText(/ask about the nz–india fta/i), 'zzzz')
    await userEvent.click(screen.getByRole('button', { name: /search/i }))

    expect(
      await screen.findByRole('heading', { name: /no verified answer — action required/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/Raise an enquiry with INZBC/)).toBeInTheDocument()
    // The failure this guards: presenting escalation as though it were a finding.
    expect(screen.queryByText(/sourced answer/i)).not.toBeInTheDocument()
  })

  it('never shows a citation or verified date on a no-match', async () => {
    mockJson(noMatch)
    render(<FtaQuery />)
    await userEvent.type(screen.getByLabelText(/ask about the nz–india fta/i), 'zzzz')
    await userEvent.click(screen.getByRole('button', { name: /search/i }))

    await screen.findByRole('heading', { name: /action required/i })
    expect(screen.queryByText(/MFAT National Interest Analysis/)).not.toBeInTheDocument()
    expect(screen.queryByRole('term', { name: /^Source$/ })).not.toBeInTheDocument()
    expect(screen.queryByText('Verified')).not.toBeInTheDocument()
  })

  it('surfaces a service failure without inventing an answer', async () => {
    mockJson({}, { ok: false, status: 503 })
    render(<FtaQuery />)
    await userEvent.type(screen.getByLabelText(/ask about the nz–india fta/i), 'wool')
    await userEvent.click(screen.getByRole('button', { name: /search/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/503/)
    expect(screen.queryByRole('article')).not.toBeInTheDocument()
  })

  it('does not submit an empty query', async () => {
    const spy = vi.fn()
    vi.stubGlobal('fetch', spy)
    render(<FtaQuery />)
    await userEvent.click(screen.getByRole('button', { name: /search/i }))
    expect(spy).not.toHaveBeenCalled()
  })

  it('pluralises the result count', async () => {
    mockJson({ ...matched, answers: [woolAnswer, { ...woolAnswer, topic: 'Sheepmeat' }] })
    render(<FtaQuery />)
    await userEvent.type(screen.getByLabelText(/ask about the nz–india fta/i), 'agriculture')
    await userEvent.click(screen.getByRole('button', { name: /search/i }))
    expect(await screen.findByRole('heading', { name: /2 sourced answers/i })).toBeInTheDocument()
  })

  it('shows a generic message when the failure is not a service error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => { throw new SyntaxError('bad json') },
    }))
    render(<FtaQuery />)
    await userEvent.type(screen.getByLabelText(/ask about the nz–india fta/i), 'wool')
    await userEvent.click(screen.getByRole('button', { name: /search/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
  })

  it('abandons an in-flight request when a second search starts', async () => {
    // Guards against a slow first response overwriting a newer result.
    const aborts: AbortSignal[] = []
    vi.stubGlobal('fetch', vi.fn().mockImplementation((_url, init) => {
      aborts.push(init.signal)
      return new Promise((resolve) =>
        setTimeout(() => resolve({ ok: true, status: 200, json: async () => matched }), 5),
      )
    }))
    render(<FtaQuery />)
    const input = screen.getByLabelText(/ask about the nz–india fta/i)
    await userEvent.type(input, 'wool')
    await userEvent.click(screen.getByRole('button', { name: /search/i }))
    await userEvent.click(screen.getByRole('button', { name: /search/i }))
    await waitFor(() => expect(aborts.length).toBeGreaterThan(1))
    expect(aborts[0]?.aborted).toBe(true)
  })

  it('announces results in a live region so the escalation is not silent', async () => {
    mockJson(noMatch)
    const { container } = render(<FtaQuery />)
    expect(container.querySelector('[aria-live="polite"]')).toBeTruthy()
    await userEvent.type(screen.getByLabelText(/ask about the nz–india fta/i), 'zzzz')
    await userEvent.click(screen.getByRole('button', { name: /search/i }))
    await waitFor(() =>
      expect(container.querySelector('[aria-live="polite"]')).toHaveTextContent(/action required/i),
    )
  })
})
