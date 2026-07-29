import type { CeoDecisionRecord, DailyBriefReport, QaChecklistGroup, ReportDecisionType } from '../domain'
import { validateBrief } from '../lib/validation'

export class ReportsApiError extends Error {}

const SIMULATED_LATENCY_MS = 350

function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Aborted', 'AbortError'))
      return
    }
    const timer = setTimeout(resolve, ms)
    signal?.addEventListener('abort', () => {
      clearTimeout(timer)
      reject(new DOMException('Aborted', 'AbortError'))
    })
  })
}

/**
 * Contract-fixture-backed stand-ins for schemas/api-contract.md's Control endpoints
 * (`POST /api/reports/:id/submit`, `POST /api/reports/:id/qa`, `POST /api/reports/:id/decision`,
 * `GET /api/dashboard`). None of these are live: `services/api/main.py` implements only the FTA
 * read path today, and the SIP endpoints "land once the database and orchestrator's persistence
 * exist" (docs/api-integration-spec.md, issue #44). Per the worklog's own instruction to build
 * against contract fixtures, every function here resolves against the in-memory report object the
 * UI already holds, with a simulated network delay so loading states are real and testable,
 * rather than issuing a `fetch()` that would just 404 against nothing. Swapping a function's body
 * for a real `fetch()` call once an endpoint exists is a small, contained change — each exported
 * signature already matches the shape schemas/api-contract.md describes (report in, updated
 * report out), and `ReportsApiError` mirrors the typed-error pattern in
 * apps/comms/ui/src/api/client.ts and apps/fta/ui/src/api/client.ts.
 */

/** POST /api/reports/:id/submit — Report Drafted -> QA In Progress. Re-validates server-side in
 * the real system; this fixture re-runs the same client-side rule so the stub can't be tricked by
 * a caller that bypasses the UI's own disabled-button gate. */
export async function submitReportForQa(
  report: DailyBriefReport,
  selectedCandidateCount: number,
  options: { signal?: AbortSignal } = {},
): Promise<DailyBriefReport> {
  const errors = validateBrief(report, selectedCandidateCount)
  if (errors.length > 0) {
    throw new ReportsApiError(`Report is not ready for QA: ${errors[0]}`)
  }
  if (report.state !== 'Report Drafted') {
    throw new ReportsApiError(`Cannot submit for QA from state "${report.state}".`)
  }
  await delay(SIMULATED_LATENCY_MS, options.signal)
  return { ...report, state: 'QA In Progress', generatedAt: report.generatedAt || new Date().toISOString() }
}

/** POST /api/reports/:id/qa — records the SIP-188 result; Critical fail routes to QA Failed. */
export async function submitQaResult(
  report: DailyBriefReport,
  checklist: QaChecklistGroup[],
  reviewer: string,
  options: { signal?: AbortSignal } = {},
): Promise<DailyBriefReport> {
  if (report.state !== 'QA In Progress') {
    throw new ReportsApiError(`Cannot record a QA result from state "${report.state}".`)
  }
  // The UI's job is to make the illegal path (reviewer === analyst) impossible to reach, not to
  // be the only thing preventing it (docs/sip-ui-spec.md) — re-checked here too, fail-closed.
  if (reviewer && reviewer === report.analyst) {
    throw new ReportsApiError('The reviewer cannot be this run\'s analyst.')
  }
  await delay(SIMULATED_LATENCY_MS, options.signal)

  const hasCriticalFail = checklist.some((group) =>
    group.items.some((item) => item.critical && item.answer === 'fail'),
  )
  const anyUnanswered = checklist.some((group) => group.items.some((item) => item.answer === null))
  const passed = !hasCriticalFail && !anyUnanswered

  return {
    ...report,
    qaChecklist: checklist,
    state: passed ? 'Awaiting CEO Decision' : 'QA Failed',
    qa: {
      reviewer,
      timestamp: new Date().toISOString(),
      result: passed ? 'Pass' : 'Fail',
      criticalFailuresFound: hasCriticalFail
        ? checklist
            .flatMap((group) => group.items)
            .filter((item) => item.critical && item.answer === 'fail')
            .map((item) => item.text)
            .join('; ')
        : '',
      correctionsRequired: passed ? '' : 'See flagged Critical items above.',
    },
  }
}

/** QA Failed -> Report Drafted — the only exit from a failed QA (docs/sip-ui-spec.md Screen 2). */
export async function returnForCorrection(
  report: DailyBriefReport,
  options: { signal?: AbortSignal } = {},
): Promise<DailyBriefReport> {
  if (report.state !== 'QA Failed') {
    throw new ReportsApiError(`Cannot return for correction from state "${report.state}".`)
  }
  await delay(SIMULATED_LATENCY_MS, options.signal)
  return { ...report, state: 'Report Drafted' }
}

/** POST /api/reports/:id/decision — two independent decisions, never combined into one submit. */
export async function recordCeoDecision(
  report: DailyBriefReport,
  decision: CeoDecisionRecord,
  options: { signal?: AbortSignal } = {},
): Promise<DailyBriefReport> {
  if (report.state !== 'Awaiting CEO Decision') {
    throw new ReportsApiError(`Cannot record a CEO decision from state "${report.state}".`)
  }
  await delay(SIMULATED_LATENCY_MS, options.signal)
  return { ...report, decision, state: resolveStateAfterDecision(decision) }
}

function resolveStateAfterDecision(decision: CeoDecisionRecord): DailyBriefReport['state'] {
  if (decision.decision === 'stop') return 'Stopped'
  if (decision.decision === 'pause') return 'Paused'
  if (decision.distributionAuthorised) return 'Approved for Manual Distribution'
  return decision.decision === 'continue_with_correction' ? 'Continue With Correction' : 'Continue'
}

export type { ReportDecisionType }
