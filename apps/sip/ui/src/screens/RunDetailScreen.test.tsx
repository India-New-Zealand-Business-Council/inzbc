import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as candidatesClient from '../api/candidatesClient'
import { SipApiError } from '../api/httpClient'
import * as runsClient from '../api/runsClient'
import { RunDetailScreen } from './RunDetailScreen'

afterEach(() => vi.restoreAllMocks())

const ACTOR_ID = '34f4237b-ecd0-470c-8b2e-424ab745eb62'

const RUN = {
  id: 'run-1',
  run_number: 'RUN-20260808-01',
  state: 'Draft',
  version: 0,
  prompt_version: 'SIP-050 v1.1',
  coverage_start_utc: '2026-08-08T00:00:00Z',
  coverage_end_utc: '2026-08-08T23:59:59Z',
  initiated_by: ACTOR_ID,
}

function stubCandidates() {
  vi.spyOn(candidatesClient, 'listCandidates').mockResolvedValue([])
}

describe('RunDetailScreen', () => {
  it('renders the run info and its (empty) candidates list', async () => {
    vi.spyOn(runsClient, 'getRun').mockResolvedValue(RUN)
    stubCandidates()
    render(<RunDetailScreen runId="run-1" onBack={vi.fn()} onSelectCandidate={vi.fn()} />)
    expect(await screen.findByRole('heading', { name: 'RUN-20260808-01' })).toBeInTheDocument()
    expect(screen.getByText('SIP-050 v1.1')).toBeInTheDocument()
    expect(await screen.findByText('No candidates captured for this run yet.')).toBeInTheDocument()
  })

  it('shows an error message when the run fails to load', async () => {
    vi.spyOn(runsClient, 'getRun').mockRejectedValue(new SipApiError("no run 'run-1'", { status: 404 }))
    render(<RunDetailScreen runId="run-1" onBack={vi.fn()} onSelectCandidate={vi.fn()} />)
    expect(await screen.findByRole('alert')).toHaveTextContent("no run 'run-1'")
  })

  it('calls onBack when the back link is clicked', async () => {
    vi.spyOn(runsClient, 'getRun').mockResolvedValue(RUN)
    stubCandidates()
    const onBack = vi.fn()
    render(<RunDetailScreen runId="run-1" onBack={onBack} onSelectCandidate={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: '← Back to runs' }))
    expect(onBack).toHaveBeenCalled()
  })

  it('runs the lifecycle action and updates the shown state in place', async () => {
    vi.spyOn(runsClient, 'getRun').mockResolvedValue(RUN)
    stubCandidates()
    vi.spyOn(runsClient, 'startRun').mockResolvedValue({ ...RUN, state: 'Run Authorised', version: 1 })

    render(<RunDetailScreen runId="run-1" onBack={vi.fn()} onSelectCandidate={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Start' }))
    await userEvent.type(screen.getByLabelText('Reason'), 'go')
    await userEvent.type(screen.getByLabelText(/Approval reference/), 'ref-1')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Start' }))

    expect(await screen.findByText('Run Authorised')).toBeInTheDocument()
  })

  it('passes candidate selection through to onSelectCandidate', async () => {
    vi.spyOn(runsClient, 'getRun').mockResolvedValue(RUN)
    vi.spyOn(candidatesClient, 'listCandidates').mockResolvedValue([
      {
        id: 'cand-1',
        run_id: 'run-1',
        headline: 'A candidate',
        source_id: null,
        url: null,
        summary: null,
        published_at: null,
        captured_at: '2026-08-08T00:00:00Z',
        in_coverage_window: null,
        nz_relevance: null,
        india_relevance: null,
        member_relevance: null,
        signal: null,
        confidence: null,
        verification: 'Unverified',
        duplicate_of: null,
        included: null,
        reason: null,
        proposed_routing: null,
      },
    ])
    const onSelectCandidate = vi.fn()
    render(<RunDetailScreen runId="run-1" onBack={vi.fn()} onSelectCandidate={onSelectCandidate} />)
    await userEvent.click(await screen.findByRole('button', { name: 'View and review' }))
    expect(onSelectCandidate).toHaveBeenCalledWith('cand-1')
  })
})
