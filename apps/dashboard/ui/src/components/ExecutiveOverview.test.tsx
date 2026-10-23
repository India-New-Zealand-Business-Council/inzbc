import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as dashboardClient from '../api/dashboardClient'
import { DashboardApiError, type DashboardOut } from '../api/dashboardClient'
import { ExecutiveOverview } from './ExecutiveOverview'

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
  qa_status: null,
}

function dashboard(overrides: Partial<DashboardOut>): DashboardOut {
  return {
    run: RUN,
    gates: { qa_status: null, report_approval: null, distribution_authority: null, distribution_recipient: null },
    coverage: { total: 0, included: 0, by_verification: {} },
    open_actions: [],
    open_actions_truncated: false,
    ...overrides,
  }
}

describe('ExecutiveOverview', () => {
  it('shows a loading state, then the current run, coverage counts and gates', async () => {
    vi.spyOn(dashboardClient, 'getDashboard').mockResolvedValue(
      dashboard({
        coverage: { total: 2, included: 1, by_verification: { Verified: 1, Unverified: 1 } },
        gates: { qa_status: 'Pass', report_approval: null, distribution_authority: null, distribution_recipient: null },
      }),
    )

    render(<ExecutiveOverview />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading dashboard…')

    expect(await screen.findByText('RUN-20260808-01')).toBeInTheDocument()
    expect(screen.getByText('Awaiting CEO Decision')).toBeInTheDocument()
    expect(screen.getByText('Total captured').nextElementSibling).toHaveTextContent('2')
    expect(screen.getByText('Included').nextElementSibling).toHaveTextContent('1')
    expect(screen.getByText('Verified').nextElementSibling).toHaveTextContent('1')
    expect(screen.getByText('Unverified').nextElementSibling).toHaveTextContent('1')
    expect(screen.getByText('QA status').nextElementSibling).toHaveTextContent('Pass')
    expect(screen.getByText('Report approval').nextElementSibling).toHaveTextContent('—')
  })

  it('shows a no-run state when there is no current run', async () => {
    vi.spyOn(dashboardClient, 'getDashboard').mockResolvedValue(dashboard({ run: null }))
    render(<ExecutiveOverview />)
    expect(await screen.findByText('No SIP runs recorded yet.')).toBeInTheDocument()
  })

  it('shows an empty coverage state when the current run has no candidates yet', async () => {
    vi.spyOn(dashboardClient, 'getDashboard').mockResolvedValue(dashboard({}))
    render(<ExecutiveOverview />)
    expect(await screen.findByText('No candidates captured for this run yet.')).toBeInTheDocument()
  })

  it('renders open actions, flagging overdue ones', async () => {
    vi.spyOn(dashboardClient, 'getDashboard').mockResolvedValue(
      dashboard({
        open_actions: [
          {
            action_code: 'ACT-1',
            title: 'Resolve Critical finding',
            owner: 'Daniel Osei',
            priority: 'Critical',
            due_date: '2026-08-10',
            status: 'Open',
            overdue: true,
          },
        ],
      }),
    )
    render(<ExecutiveOverview />)
    expect(await screen.findByText('Resolve Critical finding')).toBeInTheDocument()
    expect(screen.getByText('ACT-1 · Daniel Osei · due 2026-08-10')).toBeInTheDocument()
    expect(screen.getByText('Overdue')).toBeInTheDocument()
  })

  it('shows a note when open actions are truncated', async () => {
    vi.spyOn(dashboardClient, 'getDashboard').mockResolvedValue(dashboard({ open_actions_truncated: true }))
    render(<ExecutiveOverview />)
    expect(await screen.findByText('More open actions exist than are shown here.')).toBeInTheDocument()
  })

  it('shows "No open actions." when there are none', async () => {
    vi.spyOn(dashboardClient, 'getDashboard').mockResolvedValue(dashboard({}))
    render(<ExecutiveOverview />)
    expect(await screen.findByText('No open actions.')).toBeInTheDocument()
  })

  it('shows an error message when the dashboard fetch fails', async () => {
    vi.spyOn(dashboardClient, 'getDashboard').mockRejectedValue(new DashboardApiError('database is down'))
    render(<ExecutiveOverview />)
    expect(await screen.findByRole('alert')).toHaveTextContent('database is down')
  })

  it('aborts the previous request on Refresh so a slower older response cannot overwrite a newer one', async () => {
    let resolveFirst: (value: DashboardOut) => void = () => {}
    const signals: AbortSignal[] = []
    vi.spyOn(dashboardClient, 'getDashboard')
      .mockImplementationOnce(({ signal } = {}) => {
        signals.push(signal!)
        return new Promise<DashboardOut>((resolve) => {
          resolveFirst = resolve
        })
      })
      .mockImplementationOnce(({ signal } = {}) => {
        signals.push(signal!)
        return Promise.resolve(dashboard({ run: { ...RUN, run_number: 'RUN-NEWER' } }))
      })

    render(<ExecutiveOverview />)
    await userEvent.click(screen.getByRole('button', { name: 'Refresh' }))
    expect(await screen.findByText('RUN-NEWER')).toBeInTheDocument()
    expect(signals[0]?.aborted).toBe(true)

    // The first request resolves late, after the refresh: it must not replace the newer data.
    resolveFirst(dashboard({ run: { ...RUN, run_number: 'RUN-STALE' } }))
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(screen.getByText('RUN-NEWER')).toBeInTheDocument()
    expect(screen.queryByText('RUN-STALE')).not.toBeInTheDocument()
  })
})
