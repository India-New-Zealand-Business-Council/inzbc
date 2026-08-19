import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as candidatesClient from '../api/candidatesClient'
import { DashboardApiError } from '../api/httpClient'
import * as runsClient from '../api/runsClient'
import { SipOverview } from './SipOverview'

afterEach(() => vi.restoreAllMocks())

const RUN = {
  id: 'run-1',
  run_number: 'RUN-20260808-01',
  state: 'Awaiting CEO Decision',
  version: 2,
  prompt_version: 'SIP-050 v1.1',
  coverage_start_utc: '2026-08-08T00:00:00Z',
  coverage_end_utc: '2026-08-08T23:59:59Z',
  initiated_by: '34f4237b-ecd0-470c-8b2e-424ab745eb62',
}

function candidate(overrides: Partial<candidatesClient.CandidateOut>): candidatesClient.CandidateOut {
  return {
    id: 'c1',
    run_id: RUN.id,
    headline: 'headline',
    source_id: null,
    url: null,
    summary: null,
    published_at: null,
    captured_at: '2026-08-08T01:00:00Z',
    in_coverage_window: true,
    nz_relevance: null,
    india_relevance: null,
    member_relevance: null,
    signal: null,
    confidence: null,
    verification: 'Unverified',
    duplicate_of: null,
    included: false,
    reason: null,
    proposed_routing: null,
    ...overrides,
  }
}

describe('SipOverview', () => {
  it('shows a loading state, then the current run and its coverage counts', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([RUN])
    vi.spyOn(candidatesClient, 'listCandidates').mockResolvedValue([
      candidate({ id: 'a', verification: 'Verified', included: true }),
      candidate({ id: 'b', verification: 'Unverified' }),
    ])

    render(<SipOverview />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading current run…')

    expect(await screen.findByText('RUN-20260808-01')).toBeInTheDocument()
    expect(screen.getByText('Awaiting CEO Decision')).toBeInTheDocument()
    expect(candidatesClient.listCandidates).toHaveBeenCalledWith(RUN.id, expect.anything())
    expect(screen.getByText('Total captured').nextElementSibling).toHaveTextContent('2')
    expect(screen.getByText('Included').nextElementSibling).toHaveTextContent('1')
    expect(screen.getByText('Verified').nextElementSibling).toHaveTextContent('1')
    expect(screen.getByText('Unverified').nextElementSibling).toHaveTextContent('1')
  })

  it('shows a no-runs state when there are no runs yet', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([])
    const listCandidatesSpy = vi.spyOn(candidatesClient, 'listCandidates')
    render(<SipOverview />)
    expect(await screen.findByText('No SIP runs recorded yet.')).toBeInTheDocument()
    expect(listCandidatesSpy).not.toHaveBeenCalled()
  })

  it('shows an empty coverage state when the current run has no candidates yet', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([RUN])
    vi.spyOn(candidatesClient, 'listCandidates').mockResolvedValue([])
    render(<SipOverview />)
    expect(await screen.findByText('No candidates captured for this run yet.')).toBeInTheDocument()
  })

  it('shows an error message when fetching runs fails', async () => {
    vi.spyOn(runsClient, 'listRuns').mockRejectedValue(new DashboardApiError('database is down'))
    render(<SipOverview />)
    expect(await screen.findByRole('alert')).toHaveTextContent('database is down')
  })

  it('shows an error message when fetching candidates fails', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([RUN])
    vi.spyOn(candidatesClient, 'listCandidates').mockRejectedValue(new DashboardApiError('candidates unavailable'))
    render(<SipOverview />)
    expect(await screen.findByRole('alert')).toHaveTextContent('candidates unavailable')
  })
})
