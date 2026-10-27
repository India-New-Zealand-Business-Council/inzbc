import { completeRun, pauseRun, resumeRun, startRun, type RunOut, type TransitionIn } from '../api/runsClient'

export type RunAction = 'start' | 'pause' | 'resume' | 'complete'

export const RUN_ACTION_LABEL: Record<RunAction, string> = {
  start: 'Start',
  pause: 'Pause',
  resume: 'Resume',
  complete: 'Complete',
}

/** All three human-gated actions verify a persisted, run-bound authority.
 * Start/resume check a matching run_authorisations record and gate kind;
 * pause requires an existing decision_records row. Complete is mechanical.
 * Text input is the ID of an EXISTING record, not a free-form approval note. */
export const RUN_APPROVAL_REF_LABEL: Record<Exclude<RunAction, 'complete'>, string> = {
  start: 'Approval reference (existing launch authorisation ID for this run)',
  resume: 'Approval reference (existing resumption authorisation ID for this run)',
  pause: 'Decision record ID (required — must match an existing decision_records row)',
}

/**
 * Shared by RunsListScreen and RunDetailScreen's action panels, so the one endpoint-per-action
 * mapping lives once. A `switch` calling each function directly, not a dispatch table built from
 * an object literal (`{start: startRun, ...}`) — that captures each function's value once at
 * module load, so a test's `vi.spyOn(runsClient, 'startRun')` would silently never be seen here:
 * the table would still hold the original, pre-spy reference. A direct call site reads the live
 * (mockable) export each time instead.
 */
export function submitRunAction(action: RunAction, runId: string, body: TransitionIn): Promise<RunOut> {
  switch (action) {
    case 'start':
      return startRun(runId, body)
    case 'pause':
      return pauseRun(runId, body)
    case 'resume':
      return resumeRun(runId, body)
    case 'complete':
      return completeRun(runId, body)
  }
}
