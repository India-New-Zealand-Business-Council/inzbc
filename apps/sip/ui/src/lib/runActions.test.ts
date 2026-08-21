import { afterEach, describe, expect, it, vi } from 'vitest'
import * as runsClient from '../api/runsClient'
import { submitRunAction } from './runActions'

afterEach(() => vi.restoreAllMocks())

const RUN = {
  id: 'run-1',
  run_number: 'RUN-1',
  state: 'Draft',
  version: 0,
  prompt_version: 'v1',
  coverage_start_utc: '2026-08-08T00:00:00Z',
  coverage_end_utc: '2026-08-08T23:59:59Z',
  initiated_by: '34f4237b-ecd0-470c-8b2e-424ab745eb62',
}

const BODY = { expected_version: 0, reason: 'go', approval_ref: null }

/**
 * Each branch calls through the live export directly (not a captured dispatch table — see this
 * file's own comment for why that matters), so spying on the individual client function is what
 * actually proves the routing is correct, not just that *a* mock resolved.
 */
describe('submitRunAction', () => {
  it.each([
    ['start', 'startRun'],
    ['pause', 'pauseRun'],
    ['resume', 'resumeRun'],
    ['complete', 'completeRun'],
  ] as const)('%s calls runsClient.%s', async (action, exportName) => {
    const spy = vi.spyOn(runsClient, exportName).mockResolvedValue(RUN)
    await submitRunAction(action, RUN.id, BODY)
    expect(spy).toHaveBeenCalledWith(RUN.id, BODY)
  })
})
