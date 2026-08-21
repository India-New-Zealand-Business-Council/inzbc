import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as candidatesClient from '../api/candidatesClient'
import * as runsClient from '../api/runsClient'
import { RunsCandidatesScreen } from './RunsCandidatesScreen'

afterEach(() => vi.restoreAllMocks())

const RUN = {
  id: 'run-1',
  run_number: 'RUN-20260808-01',
  state: 'Draft',
  version: 0,
  prompt_version: 'SIP-050 v1.1',
  coverage_start_utc: '2026-08-08T00:00:00Z',
  coverage_end_utc: '2026-08-08T23:59:59Z',
  initiated_by: '34f4237b-ecd0-470c-8b2e-424ab745eb62',
}

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

describe('RunsCandidatesScreen', () => {
  it('navigates runs list -> run detail -> candidate detail and back again', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([RUN])
    vi.spyOn(runsClient, 'getRun').mockResolvedValue(RUN)
    vi.spyOn(candidatesClient, 'listCandidates').mockResolvedValue([CANDIDATE])
    vi.spyOn(candidatesClient, 'getCandidate').mockResolvedValue(CANDIDATE)

    render(<RunsCandidatesScreen />)

    await userEvent.click(await screen.findByRole('button', { name: 'View run and candidates' }))
    expect(await screen.findByRole('heading', { name: 'RUN-20260808-01' })).toBeInTheDocument()

    await userEvent.click(await screen.findByRole('button', { name: 'View and review' }))
    expect(await screen.findByRole('heading', { name: 'A candidate headline' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: '← Back to run' }))
    expect(await screen.findByRole('heading', { name: 'RUN-20260808-01' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: '← Back to runs' }))
    expect(await screen.findByRole('heading', { name: 'Runs' })).toBeInTheDocument()
  })
})
