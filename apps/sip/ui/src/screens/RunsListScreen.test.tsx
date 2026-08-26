import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as runsClient from '../api/runsClient'
import { SipApiError } from '../api/httpClient'
import { RunsListScreen } from './RunsListScreen'

afterEach(() => vi.restoreAllMocks())

const ACTOR_ID = '34f4237b-ecd0-470c-8b2e-424ab745eb62'

const DRAFT_RUN = {
  id: 'run-1',
  run_number: 'RUN-20260808-01',
  state: 'Draft',
  version: 0,
  prompt_version: 'SIP-050 v1.1',
  coverage_start_utc: '2026-08-08T00:00:00Z',
  coverage_end_utc: '2026-08-08T23:59:59Z',
  initiated_by: ACTOR_ID,
}

describe('RunsListScreen', () => {
  it('shows a loading state, then the fetched runs', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([DRAFT_RUN])
    render(<RunsListScreen onSelectRun={vi.fn()} />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading runs…')
    expect(await screen.findByText('RUN-20260808-01')).toBeInTheDocument()
    expect(screen.getByText('Draft')).toBeInTheDocument()
  })

  it('shows an empty state when there are no runs', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([])
    render(<RunsListScreen onSelectRun={vi.fn()} />)
    expect(await screen.findByText('No runs recorded yet.')).toBeInTheDocument()
  })

  it('shows an error message on fetch failure', async () => {
    vi.spyOn(runsClient, 'listRuns').mockRejectedValue(new SipApiError('database is down'))
    render(<RunsListScreen onSelectRun={vi.fn()} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('database is down')
  })

  it('calls onSelectRun when "View run and candidates" is clicked', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([DRAFT_RUN])
    const onSelectRun = vi.fn()
    render(<RunsListScreen onSelectRun={onSelectRun} />)
    await userEvent.click(await screen.findByRole('button', { name: 'View run and candidates' }))
    expect(onSelectRun).toHaveBeenCalledWith('run-1')
  })

  it('offers Start for a Draft run, and submits it with the entered reason/approval', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([DRAFT_RUN])
    const startSpy = vi
      .spyOn(runsClient, 'startRun')
      .mockResolvedValue({ ...DRAFT_RUN, state: 'Run Authorised', version: 1 })

    render(<RunsListScreen onSelectRun={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Start' }))
    await userEvent.type(screen.getByLabelText('Reason'), 'Launching the run')
    await userEvent.type(screen.getByLabelText(/Approval reference/), 'launch-approval-1')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Start' }))

    expect(startSpy).toHaveBeenCalledWith(
      'run-1',
      expect.objectContaining({
        expected_version: 0,
        reason: 'Launching the run',
        approval_ref: 'launch-approval-1',
      }),
    )
    // Reloads the list on success — listRuns called once on mount, once after the action.
    expect(runsClient.listRuns).toHaveBeenCalledTimes(2)
  })

  it('requires a reason before submitting an action', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([DRAFT_RUN])
    const startSpy = vi.spyOn(runsClient, 'startRun')
    render(<RunsListScreen onSelectRun={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Start' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Start' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('A reason is required.')
    expect(startSpy).not.toHaveBeenCalled()
  })

  it('surfaces a 409 conflict from the server as an alert, without reloading', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([DRAFT_RUN])
    vi.spyOn(runsClient, 'startRun').mockRejectedValue(new SipApiError('version mismatch', { status: 409 }))
    render(<RunsListScreen onSelectRun={vi.fn()} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Start' }))
    await userEvent.type(screen.getByLabelText('Reason'), 'go')
    await userEvent.type(screen.getByLabelText(/Approval reference/), 'ref-1')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Start' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('version mismatch')
    expect(runsClient.listRuns).toHaveBeenCalledTimes(1)
  })

  it('does not offer an action button for a state with no legal next action', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([{ ...DRAFT_RUN, state: 'Closed' }])
    render(<RunsListScreen onSelectRun={vi.fn()} />)
    await screen.findByText('RUN-20260808-01')
    expect(screen.queryByRole('button', { name: 'Start' })).not.toBeInTheDocument()
  })
})
