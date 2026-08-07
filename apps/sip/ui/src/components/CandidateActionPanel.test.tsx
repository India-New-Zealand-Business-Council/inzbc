import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as candidatesClient from '../api/candidatesClient'
import { SipApiError } from '../api/httpClient'
import { CandidateActionPanel } from './CandidateActionPanel'

afterEach(() => vi.restoreAllMocks())

const ACTOR_ID = '34f4237b-ecd0-470c-8b2e-424ab745eb62'

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

describe('CandidateActionPanel', () => {
  it('requires an "acting as" id before any action can submit', async () => {
    const verifySpy = vi.spyOn(candidatesClient, 'verifyCandidate')
    render(<CandidateActionPanel candidate={CANDIDATE} actorId="not-a-uuid" onUpdated={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Verify' }))
    await userEvent.type(screen.getByLabelText('Reason'), 'go')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Verify' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Acting as')
    expect(verifySpy).not.toHaveBeenCalled()
  })

  it('requires a reason before any action can submit', async () => {
    render(<CandidateActionPanel candidate={CANDIDATE} actorId={ACTOR_ID} onUpdated={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Verify' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Verify' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('A reason is required.')
  })

  it('submits verify with the selected verification state', async () => {
    const spy = vi.spyOn(candidatesClient, 'verifyCandidate').mockResolvedValue({ ...CANDIDATE, verification: 'Rejected' })
    const onUpdated = vi.fn()
    render(<CandidateActionPanel candidate={CANDIDATE} actorId={ACTOR_ID} onUpdated={onUpdated} />)
    await userEvent.click(screen.getByRole('button', { name: 'Verify' }))
    await userEvent.selectOptions(screen.getByLabelText('Verification'), 'Rejected')
    await userEvent.type(screen.getByLabelText('Reason'), 'source is not credible')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Verify' }))
    expect(spy).toHaveBeenCalledWith('cand-1', {
      verification: 'Rejected',
      actor_id: ACTOR_ID,
      reason: 'source is not credible',
    })
    expect(onUpdated).toHaveBeenCalledWith({ ...CANDIDATE, verification: 'Rejected' })
  })

  it('submits score with relevance clamped to 0-5 and clears unset fields to null', async () => {
    const spy = vi.spyOn(candidatesClient, 'scoreCandidate').mockResolvedValue(CANDIDATE)
    render(<CandidateActionPanel candidate={CANDIDATE} actorId={ACTOR_ID} onUpdated={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Score' }))
    await userEvent.type(screen.getByLabelText('NZ relevance (0-5)'), '9')
    await userEvent.type(screen.getByLabelText('India relevance (0-5)'), '2')
    await userEvent.type(screen.getByLabelText('Reason'), 'scoring')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Score' }))
    expect(spy).toHaveBeenCalledWith('cand-1', {
      nz_relevance: 5,
      india_relevance: 2,
      member_relevance: null,
      signal: null,
      confidence: null,
      actor_id: ACTOR_ID,
      reason: 'scoring',
    })
  })

  it('surfaces the verification-gate 403 message from the server on score', async () => {
    vi.spyOn(candidatesClient, 'scoreCandidate').mockRejectedValue(
      new SipApiError('High signal requires a verified source (got verification=Unverified)', { status: 403 }),
    )
    render(<CandidateActionPanel candidate={CANDIDATE} actorId={ACTOR_ID} onUpdated={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Score' }))
    await userEvent.selectOptions(screen.getByLabelText('Signal'), 'High')
    await userEvent.type(screen.getByLabelText('Reason'), 'scoring')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Score' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('requires a verified source')
  })

  it('submits route with proposed routing and included', async () => {
    const spy = vi.spyOn(candidatesClient, 'routeCandidate').mockResolvedValue({ ...CANDIDATE, included: true })
    render(<CandidateActionPanel candidate={CANDIDATE} actorId={ACTOR_ID} onUpdated={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Route' }))
    await userEvent.type(screen.getByLabelText('Proposed routing'), 'weekly-digest')
    await userEvent.click(screen.getByLabelText('Include in the brief'))
    await userEvent.type(screen.getByLabelText('Reason'), 'routing')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Route' }))
    expect(spy).toHaveBeenCalledWith('cand-1', {
      proposed_routing: 'weekly-digest',
      included: true,
      actor_id: ACTOR_ID,
      reason: 'routing',
    })
  })

  it('requires a duplicate-of id before merge can submit', async () => {
    const spy = vi.spyOn(candidatesClient, 'mergeCandidate')
    render(<CandidateActionPanel candidate={CANDIDATE} actorId={ACTOR_ID} onUpdated={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Merge' }))
    await userEvent.type(screen.getByLabelText('Reason'), 'duplicate')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Merge' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('duplicate-of candidate id is required')
    expect(spy).not.toHaveBeenCalled()
  })

  it('submits merge with the duplicate-of id', async () => {
    const spy = vi.spyOn(candidatesClient, 'mergeCandidate').mockResolvedValue({ ...CANDIDATE, duplicate_of: 'cand-2' })
    render(<CandidateActionPanel candidate={CANDIDATE} actorId={ACTOR_ID} onUpdated={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Merge' }))
    await userEvent.type(screen.getByLabelText('Duplicate of (candidate id)'), 'cand-2')
    await userEvent.type(screen.getByLabelText('Reason'), 'same story')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Merge' }))
    expect(spy).toHaveBeenCalledWith('cand-1', { duplicate_of: 'cand-2', actor_id: ACTOR_ID, reason: 'same story' })
  })

  it('switching actions clears the previous action’s panel', async () => {
    render(<CandidateActionPanel candidate={CANDIDATE} actorId={ACTOR_ID} onUpdated={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Verify' }))
    expect(screen.getByLabelText('Verification')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Score' }))
    expect(screen.queryByLabelText('Verification')).not.toBeInTheDocument()
    expect(screen.getByLabelText('NZ relevance (0-5)')).toBeInTheDocument()
  })
})
