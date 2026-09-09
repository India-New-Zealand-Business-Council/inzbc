import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as runsClient from '../api/runsClient'
import type { RunOut } from '../api/runsClient'
import { AppShell } from './AppShell'

function run(overrides: Partial<RunOut> = {}): RunOut {
  return {
    id: 'run-open',
    run_number: 'RUN-20260908-01',
    state: 'Report Drafted',
    version: 5,
    prompt_version: 'SIP-050 v1.1',
    coverage_start_utc: '2026-09-07T00:00:00+00:00',
    coverage_end_utc: '2026-09-07T20:00:00+00:00',
    initiated_by: 'user-1',
    qa_status: null,
    ...overrides,
  }
}

afterEach(() => {
  vi.restoreAllMocks()
})

/** The line naming which run the workflow screens follow. The run number also appears inside the
 *  screens themselves, so assertions about the banner have to say they mean the banner. */
function workingRunBanner(): HTMLElement {
  return screen.getByText(/Working run/i).closest('p') as HTMLElement
}

describe('AppShell', () => {
  it('opens on the platform overview', async () => {
    // Was Brief Builder, when this shell was one tool. With four modules behind it, landing on
    // any single module's first screen hides the other three.
    render(<AppShell />)
    expect(screen.getByRole('heading', { level: 1, name: /inzbc platform/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Brief Builder' }))
    expect(screen.getByRole('heading', { level: 1, name: /brief builder/i })).toBeInTheDocument()
  })

  it('switches screens via the nav, marking the active tab with aria-current', async () => {
    render(<AppShell />)
    const qaTab = screen.getByRole('button', { name: 'QA Review' })
    expect(qaTab).not.toHaveAttribute('aria-current')

    await userEvent.click(qaTab)

    expect(screen.getByRole('heading', { level: 2, name: /qa review/i })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 2, name: /brief builder/i })).not.toBeInTheDocument()
    expect(qaTab).toHaveAttribute('aria-current', 'page')
  })

  it('reaches every module from the one nav', async () => {
    // The whole point of the shell: one running app, not five. If a tab stops resolving to its
    // module this fails, which is what a demo depends on.
    render(<AppShell />)

    await userEvent.click(screen.getByRole('button', { name: 'CEO Decision' }))
    expect(screen.getByRole('heading', { level: 1, name: /ceo decision/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Distribution' }))
    expect(screen.getByRole('heading', { level: 1, name: /distribution/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'FTA Explainer' }))
    expect(screen.getByRole('heading', { level: 1, name: /fta explainer/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Comms Assistant' }))
    expect(screen.getByRole('heading', { level: 1, name: /comms assistant/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Member Portal' }))
    expect(screen.getByRole('heading', { level: 1, name: /member portal/i })).toBeInTheDocument()
  })

  it("opens on the newest run that has not finished", async () => {
    // Newest first, as the API returns them. The finished run is newer, and is still not the one
    // someone arriving at the tool is working on.
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([
      run({ id: 'run-done', run_number: 'RUN-DONE', state: 'Distributed' }),
      run({ id: 'run-open', run_number: 'RUN-OPEN', state: 'Report Drafted' }),
    ])
    render(<AppShell />)

    await userEvent.click(screen.getByRole('button', { name: 'Brief Builder' }))
    await waitFor(() => expect(screen.getByText(/Working run/i)).toBeInTheDocument())
    const banner = workingRunBanner()
    expect(within(banner).getByText('RUN-OPEN')).toBeInTheDocument()
    expect(banner).toHaveTextContent('Report Drafted')
    expect(banner).not.toHaveTextContent('RUN-DONE')
  })

  it("falls back to the newest run when every run has finished", async () => {
    // A real closed run is a truer thing to show than a run number that exists nowhere.
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([
      run({ id: 'run-a', run_number: 'RUN-CLOSED', state: 'Closed' }),
      run({ id: 'run-b', run_number: 'RUN-OLDER', state: 'Stopped' }),
    ])
    render(<AppShell />)

    await userEvent.click(screen.getByRole('button', { name: 'Distribution' }))
    await waitFor(() => expect(screen.getByText(/Working run/i)).toBeInTheDocument())
    expect(within(workingRunBanner()).getByText('RUN-CLOSED')).toBeInTheDocument()
  })

  it("says no run is selected rather than naming one when the runs cannot be loaded", async () => {
    vi.spyOn(runsClient, 'listRuns').mockRejectedValue(new Error('unreachable'))
    render(<AppShell />)

    await userEvent.click(screen.getByRole('button', { name: 'QA Review' }))
    await waitFor(() =>
      expect(screen.getByText(/No run selected yet/i)).toBeInTheDocument(),
    )
  })

  it("names the working run only on the screens that act on one", async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([run({ run_number: 'RUN-OPEN' })])
    render(<AppShell />)

    await userEvent.click(screen.getByRole('button', { name: 'Brief Builder' }))
    await waitFor(() => expect(screen.getByText(/Working run/i)).toBeInTheDocument())

    // The overview describes the instance, not one run, so naming a run there would be noise.
    await userEvent.click(screen.getByRole('button', { name: 'Overview' }))
    expect(screen.queryByText(/Working run/i)).not.toBeInTheDocument()
  })
})
