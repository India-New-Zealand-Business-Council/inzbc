import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as candidatesClient from '../api/candidatesClient'
import { SipApiError } from '../api/httpClient'
import { CandidatesListScreen } from './CandidatesListScreen'

afterEach(() => vi.restoreAllMocks())

const CANDIDATE = {
  id: 'cand-1',
  run_id: 'run-1',
  headline: 'A candidate headline',
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
  verification: 'Unverified' as const,
  duplicate_of: null,
  included: null,
  reason: null,
  proposed_routing: null,
}

describe('CandidatesListScreen', () => {
  it('lists candidates for the given run', async () => {
    const spy = vi.spyOn(candidatesClient, 'listCandidates').mockResolvedValue([CANDIDATE])
    render(<CandidatesListScreen runId="run-1" onSelectCandidate={vi.fn()} />)
    expect(await screen.findByText('A candidate headline')).toBeInTheDocument()
    expect(spy).toHaveBeenCalledWith('run-1', expect.anything())
  })

  it('shows an error message on fetch failure', async () => {
    vi.spyOn(candidatesClient, 'listCandidates').mockRejectedValue(new SipApiError('run not found', { status: 404 }))
    render(<CandidatesListScreen runId="run-1" onSelectCandidate={vi.fn()} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('run not found')
  })

  it('calls onSelectCandidate when "View and review" is clicked', async () => {
    vi.spyOn(candidatesClient, 'listCandidates').mockResolvedValue([CANDIDATE])
    const onSelectCandidate = vi.fn()
    render(<CandidatesListScreen runId="run-1" onSelectCandidate={onSelectCandidate} />)
    await userEvent.click(await screen.findByRole('button', { name: 'View and review' }))
    expect(onSelectCandidate).toHaveBeenCalledWith('cand-1')
  })

  it('updates a candidate in place after a successful action, without re-fetching', async () => {
    const listSpy = vi.spyOn(candidatesClient, 'listCandidates').mockResolvedValue([CANDIDATE])
    vi.spyOn(candidatesClient, 'verifyCandidate').mockResolvedValue({ ...CANDIDATE, verification: 'Verified' })

    render(<CandidatesListScreen runId="run-1" onSelectCandidate={vi.fn()} />)
    await screen.findByText('A candidate headline')
    await userEvent.click(screen.getByRole('button', { name: 'Verify' }))
    await userEvent.type(screen.getByLabelText('Reason'), 'confirmed via primary source')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Verify' }))

    expect(await screen.findByText('Verified')).toBeInTheDocument()
    expect(listSpy).toHaveBeenCalledTimes(1)
  })
})
