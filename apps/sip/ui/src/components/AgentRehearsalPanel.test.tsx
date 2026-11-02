import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SipApiError } from '../api/httpClient'
import * as runsClient from '../api/runsClient'
import type { RehearsalOut } from '../api/runsClient'
import { AgentRehearsalPanel } from './AgentRehearsalPanel'

afterEach(() => vi.restoreAllMocks())

const REHEARSAL: RehearsalOut = {
  id: 'reh-1',
  run_id: 'run-1',
  started_by: 'user-1',
  started_at: '2026-10-24T01:00:00+00:00',
  outcome: 'reached_qa',
  stop_reason: null,
  final_state: 'QA In Progress',
  steps: 2,
  accepted: 2,
  refused: 0,
  candidates: 0,
  brief_summary: 'No material new signal in this window.',
  production_enabled: false,
  chain_head: 'a'.repeat(64),
  sealed: true,
  tool_steps: [
    {
      sequence: 0,
      tool: 'lock_coverage_window',
      reason: 'Lock the window.',
      outcome: 'accepted',
      detail: 'locked 24h coverage window',
      state_before: 'Run Authorised',
      state_after: 'Coverage Locked',
      at: '2026-10-24T01:00:00+00:00',
    },
    {
      sequence: 1,
      tool: 'advance_state',
      reason: 'Skip QA.',
      outcome: 'refused',
      detail: 'HumanGateRequired',
      state_before: 'Report Drafted',
      state_after: 'Report Drafted',
      at: '2026-10-24T01:00:01+00:00',
    },
  ],
  verification: { chain_intact: true, seal: 'valid', replay: 'exact' },
}

describe('AgentRehearsalPanel', () => {
  it('lists past rehearsals with their re-verified trail', async () => {
    vi.spyOn(runsClient, 'listRehearsals').mockResolvedValue([REHEARSAL])
    render(<AgentRehearsalPanel runId="run-1" runState="Run Authorised" />)

    expect(await screen.findByText('Stopped at the QA gate · QA In Progress')).toBeInTheDocument()
    expect(screen.getByText('Trail verified')).toBeInTheDocument()
  })

  it('wires the disclosure button to the region it controls for screen readers', async () => {
    vi.spyOn(runsClient, 'listRehearsals').mockResolvedValue([REHEARSAL])
    render(<AgentRehearsalPanel runId="run-1" runState="Run Authorised" />)

    const toggle = await screen.findByRole('button', { name: /Stopped at the QA gate/ })
    const controlsId = toggle.getAttribute('aria-controls')
    expect(controlsId).toBeTruthy()
    expect(document.getElementById(controlsId as string)).toBeNull()

    await userEvent.click(toggle)
    expect(document.getElementById(controlsId as string)).toBe(screen.getByText('Draft brief:').closest('div'))
  })

  it('runs the agent and opens the new trail, including refused steps', async () => {
    vi.spyOn(runsClient, 'listRehearsals').mockResolvedValue([])
    const start = vi.spyOn(runsClient, 'startRehearsal').mockResolvedValue(REHEARSAL)
    render(<AgentRehearsalPanel runId="run-1" runState="Run Authorised" />)

    expect(await screen.findByText('No rehearsals yet.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Run the agent' }))

    expect(start).toHaveBeenCalledWith('run-1')
    const steps = await screen.findByRole('list', { name: 'Agent steps' })
    expect(steps).toHaveTextContent('lock_coverage_window')
    expect(steps).toHaveTextContent('Refused')
    expect(screen.getByText('Seal verified')).toBeInTheDocument()
    expect(screen.getByText('No material new signal in this window.')).toBeInTheDocument()
  })

  it('flags a trail whose check failed', async () => {
    vi.spyOn(runsClient, 'listRehearsals').mockResolvedValue([
      { ...REHEARSAL, verification: { chain_intact: false, seal: 'invalid', replay: 'refused: edited' } },
    ])
    render(<AgentRehearsalPanel runId="run-1" runState="Run Authorised" />)

    await userEvent.click(await screen.findByRole('button', { name: /Trail check failed/ }))
    expect(screen.getByText('Broken')).toBeInTheDocument()
    expect(screen.getByText('Seal does not verify')).toBeInTheDocument()
    expect(screen.getByText('refused: edited')).toBeInTheDocument()
  })

  it.each(['unsealed', 'key-not-configured'] as const)('does not claim a %s trail is verified', async (seal) => {
    vi.spyOn(runsClient, 'listRehearsals').mockResolvedValue([
      { ...REHEARSAL, verification: { chain_intact: true, seal, replay: 'exact' } },
    ])
    render(<AgentRehearsalPanel runId="run-1" runState="Run Authorised" />)

    const neutral = await screen.findByText('Seal not verified')
    expect(neutral).toHaveClass('bg-slate-100')
    expect(screen.queryByText('Trail verified')).not.toBeInTheDocument()
    expect(screen.queryByText('Trail check failed')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Seal not verified/ }))
    expect(screen.getByText(seal === 'unsealed' ? 'Not sealed (no signing key)' : 'Sealed; key not available to check')).toBeInTheDocument()
  })

  it('reports a failed replay even if the seal itself verifies', async () => {
    vi.spyOn(runsClient, 'listRehearsals').mockResolvedValue([
      { ...REHEARSAL, verification: { chain_intact: true, seal: 'valid', replay: 'different' } },
    ])
    render(<AgentRehearsalPanel runId="run-1" runState="Run Authorised" />)
    expect(await screen.findByText('Trail check failed')).toBeInTheDocument()
  })

  it('cannot run before launch authority is recorded', async () => {
    vi.spyOn(runsClient, 'listRehearsals').mockResolvedValue([])
    render(<AgentRehearsalPanel runId="run-1" runState="Draft" />)

    expect(screen.getByRole('button', { name: 'Run the agent' })).toBeDisabled()
    expect(screen.getByText(/has to start the run/)).toBeInTheDocument()
    expect(await screen.findByText('No rehearsals yet.')).toBeInTheDocument()
  })

  it('shows why the server refused to run the agent', async () => {
    vi.spyOn(runsClient, 'listRehearsals').mockResolvedValue([])
    vi.spyOn(runsClient, 'startRehearsal').mockRejectedValue(
      new SipApiError('OPENAI_API_KEY is not set - the gateway will not fabricate a response.', { status: 503 }),
    )
    render(<AgentRehearsalPanel runId="run-1" runState="Run Authorised" />)

    await userEvent.click(await screen.findByRole('button', { name: 'Run the agent' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('OPENAI_API_KEY is not set')
  })

  it('shows a load failure', async () => {
    vi.spyOn(runsClient, 'listRehearsals').mockRejectedValue(new Error('boom'))
    render(<AgentRehearsalPanel runId="run-1" runState="Run Authorised" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Something went wrong')
  })

  it('refreshes the list to pick up a rehearsal started elsewhere', async () => {
    const list = vi.spyOn(runsClient, 'listRehearsals').mockResolvedValueOnce([])
    render(<AgentRehearsalPanel runId="run-1" runState="Run Authorised" />)
    expect(await screen.findByText('No rehearsals yet.')).toBeInTheDocument()

    list.mockResolvedValueOnce([REHEARSAL])
    await userEvent.click(screen.getByRole('button', { name: 'Refresh' }))

    expect(await screen.findByText('Stopped at the QA gate · QA In Progress')).toBeInTheDocument()
    expect(list).toHaveBeenCalledTimes(2)
  })
})
