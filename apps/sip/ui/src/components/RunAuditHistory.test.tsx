import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import * as auditClient from '../api/auditClient'
import { RunAuditHistory } from './RunAuditHistory'

afterEach(() => vi.restoreAllMocks())

function event(id: number): auditClient.AuditEntryOut {
  return {
    id,
    at: '2026-10-28T00:00:00+00:00',
    user_id: '00000000-0000-0000-0000-0000000000aa',
    action: `run.event.${id}`,
    record_type: 'run',
    record_id: 'run-1',
    old_value: 'confidential old payload',
    new_value: 'confidential new payload',
    reason: 'confidential operator explanation',
    approval_ref: null,
  }
}

it('renders run-specific audit metadata without exposing raw values or reasons', async () => {
  const fetchAudit = vi.spyOn(auditClient, 'listRunAudit').mockResolvedValue({
    entries: [event(3)],
    next_before_id: null,
  })
  render(<RunAuditHistory runId="run-1" />)
  expect(await screen.findByText('run.event.3')).toBeInTheDocument()
  expect(fetchAudit).toHaveBeenCalledWith('run-1', undefined, expect.any(Object))
  expect(screen.queryByText(/confidential/)).not.toBeInTheDocument()
  expect(screen.getByText('Audit history')).toBeInTheDocument()
})

it('loads older entries using the server keyset cursor', async () => {
  const fetchAudit = vi.spyOn(auditClient, 'listRunAudit')
    .mockResolvedValueOnce({ entries: [event(3)], next_before_id: 3 })
    .mockResolvedValueOnce({ entries: [event(2)], next_before_id: null })
  render(<RunAuditHistory runId="run-1" />)
  await screen.findByText('run.event.3')
  await userEvent.click(screen.getByRole('button', { name: 'Load older entries' }))
  expect(await screen.findByText('run.event.2')).toBeInTheDocument()
  expect(screen.getByText('run.event.3')).toBeInTheDocument()
  expect(fetchAudit).toHaveBeenNthCalledWith(2, 'run-1', 3, expect.any(Object))
  expect(screen.queryByRole('button', { name: 'Load older entries' })).not.toBeInTheDocument()
})

it('shows an error rather than pretending the audit is empty', async () => {
  vi.spyOn(auditClient, 'listRunAudit').mockRejectedValue(new Error('offline'))
  render(<RunAuditHistory runId="run-1" />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load audit history')
})
