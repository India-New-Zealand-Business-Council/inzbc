import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as candidatesClient from '../api/candidatesClient'
import { SipApiError } from '../api/httpClient'
import { CandidateDetailScreen } from './CandidateDetailScreen'

afterEach(() => vi.restoreAllMocks())

const ACTOR_ID = '34f4237b-ecd0-470c-8b2e-424ab745eb62'

const CANDIDATE = {
  id: 'cand-1',
  run_id: 'run-1',
  headline: 'A candidate headline',
  source_id: null,
  url: 'https://example.com/article',
  summary: 'A short summary.',
  published_at: null,
  captured_at: '2026-08-08T00:00:00Z',
  in_coverage_window: true,
  nz_relevance: 4,
  india_relevance: 3,
  member_relevance: null,
  signal: 'Medium' as const,
  confidence: 'High' as const,
  verification: 'Unverified' as const,
  duplicate_of: null,
  included: null,
  reason: null,
  proposed_routing: null,
}

describe('CandidateDetailScreen', () => {
  it('renders the candidate detail', async () => {
    vi.spyOn(candidatesClient, 'getCandidate').mockResolvedValue(CANDIDATE)
    render(<CandidateDetailScreen candidateId="cand-1" actorId={ACTOR_ID} onBack={vi.fn()} />)
    expect(await screen.findByRole('heading', { name: 'A candidate headline' })).toBeInTheDocument()
    expect(screen.getByText('A short summary.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'https://example.com/article' })).toHaveAttribute(
      'href',
      'https://example.com/article',
    )
  })

  it('shows an error message when the candidate fails to load', async () => {
    vi.spyOn(candidatesClient, 'getCandidate').mockRejectedValue(new SipApiError("no candidate 'cand-1'", { status: 404 }))
    render(<CandidateDetailScreen candidateId="cand-1" actorId={ACTOR_ID} onBack={vi.fn()} />)
    expect(await screen.findByRole('alert')).toHaveTextContent("no candidate 'cand-1'")
  })

  it('calls onBack when the back link is clicked', async () => {
    vi.spyOn(candidatesClient, 'getCandidate').mockResolvedValue(CANDIDATE)
    const onBack = vi.fn()
    render(<CandidateDetailScreen candidateId="cand-1" actorId={ACTOR_ID} onBack={onBack} />)
    await userEvent.click(await screen.findByRole('button', { name: '← Back to run' }))
    expect(onBack).toHaveBeenCalled()
  })

  it('updates the shown detail after a successful action', async () => {
    vi.spyOn(candidatesClient, 'getCandidate').mockResolvedValue(CANDIDATE)
    vi.spyOn(candidatesClient, 'verifyCandidate').mockResolvedValue({ ...CANDIDATE, verification: 'Verified' })

    render(<CandidateDetailScreen candidateId="cand-1" actorId={ACTOR_ID} onBack={vi.fn()} />)
    await screen.findByRole('heading', { name: 'A candidate headline' })
    await userEvent.click(screen.getByRole('button', { name: 'Verify' }))
    await userEvent.type(screen.getByLabelText('Reason'), 'confirmed')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Verify' }))

    expect(await screen.findAllByText('Verified')).not.toHaveLength(0)
  })
})
