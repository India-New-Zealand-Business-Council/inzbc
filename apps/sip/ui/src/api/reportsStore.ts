import type { CeoDecisionRecord, DailyBriefReport, QaChecklistGroup, ReportDecisionType } from '../domain'
import { generatedDigestContent } from '../lib/fixtures'
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
  // Stands in for the pipeline generating the digest content from the selected candidates —
  // see lib/fixtures.ts's generatedDigestContent() docstring for why this is fixture data.
  return {
    ...report,
    ...generatedDigestContent(),
    state: 'QA In Progress',
    generatedAt: report.generatedAt || new Date().toISOString(),
  }
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

/**
 * POST /api/reports/:id/decision (decision 1 of 2) — the report decision only.
 *
 * docs/sip-ui-spec.md Screen 3: "Two separate, sequential decisions — never presented as one
 * combined control ... The UI must not let the CEO set [distribution authorisation] in the same
 * submit as decision 1." An earlier version of this function accepted a full `CeoDecisionRecord`
 * including `distributionAuthorised` in the same call, which made that illegal combination
 * possible to construct even if the UI never rendered it that way — the parameter type now
 * excludes those fields outright so the two decisions can't be recombined by a future caller
 * either. `authoriseDistribution` below is the separate, second action.
 */
export async function recordCeoDecision(
  report: DailyBriefReport,
  decision: Omit<CeoDecisionRecord, 'distributionAuthorised' | 'distributionDecidedAt'>,
  options: { signal?: AbortSignal } = {},
): Promise<DailyBriefReport> {
  if (report.state !== 'Awaiting CEO Decision') {
    throw new ReportsApiError(`Cannot record a CEO decision from state "${report.state}".`)
  }
  if (!decision.decision) {
    throw new ReportsApiError(
      'A report decision (Continue / Continue With Correction / Pause / Stop) is required.',
    )
  }
  await delay(SIMULATED_LATENCY_MS, options.signal)
  return {
    ...report,
    decision: { ...decision, distributionAuthorised: null, distributionDecidedAt: null },
    state: resolveStateAfterDecision(decision.decision),
  }
}

function resolveStateAfterDecision(decision: ReportDecisionType): DailyBriefReport['state'] {
  if (decision === 'stop') return 'Stopped'
  if (decision === 'pause') return 'Paused'
  return decision === 'continue_with_correction' ? 'Continue With Correction' : 'Continue'
}

/**
 * POST /api/reports/:id/decision (decision 2 of 2) — distribution authorisation.
 *
 * Only reachable once a report decision is already recorded, and only from the two states a
 * distribution question is meaningful for (`Continue` / `Continue With Correction`) — a Paused or
 * Stopped run doesn't reach this question. `authorised: false` is a complete, valid outcome
 * (docs/sip-ui-spec.md: "not an error or incomplete state") — the run simply stays in its current
 * state, proceeding to close-out with distribution skipped, rather than needing a further
 * transition.
 */
export async function authoriseDistribution(
  report: DailyBriefReport,
  authorised: boolean,
  options: { signal?: AbortSignal } = {},
): Promise<DailyBriefReport> {
  if (!report.decision) {
    throw new ReportsApiError('Cannot authorise distribution before a report decision is recorded.')
  }
  if (report.decision.distributionDecidedAt) {
    throw new ReportsApiError('Distribution has already been decided for this run.')
  }
  if (report.state !== 'Continue' && report.state !== 'Continue With Correction') {
    throw new ReportsApiError(`Cannot authorise distribution from state "${report.state}".`)
  }
  await delay(SIMULATED_LATENCY_MS, options.signal)
  return {
    ...report,
    decision: {
      ...report.decision,
      distributionAuthorised: authorised,
      distributionDecidedAt: new Date().toISOString(),
    },
    state: authorised ? 'Approved for Manual Distribution' : report.state,
  }
}

export type { ReportDecisionType }
