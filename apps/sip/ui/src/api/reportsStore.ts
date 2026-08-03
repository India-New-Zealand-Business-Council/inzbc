import type { CeoDecisionRecord, DailyBriefReport, QaChecklistGroup, ReportDecisionType } from '../domain'
import { candidatesFixture, generatedDigestContent, qaChecklistFixture } from '../lib/fixtures'
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

/** Numeric suffix of a "v<N>" version string, bumped by one — "v1" -> "v2". Falls back to "v2" for
 * anything that doesn't parse, so a resubmission always visibly advances rather than silently
 * repeating the same version string. */
function bumpReportVersion(version: string): string {
  const match = /^v(\d+)$/.exec(version.trim())
  const next = match ? Number(match[1]) + 1 : 2
  return `v${next}`
}

/** POST /api/reports/:id/submit — Report Drafted -> QA In Progress. Re-validates server-side in
 * the real system; this fixture re-runs the same client-side rule so the stub can't be tricked by
 * a caller that bypasses the UI's own disabled-button gate.
 *
 * Takes only `report` — `report.selectedCandidateIds` is the boundary, not a count. An earlier
 * version took a bare `selectedCandidateCount`, so the actual selected candidates never reached
 * `generatedDigestContent`, which returned the same two hardcoded signals regardless of what was
 * selected. Resolving ids to candidates here (rather than requiring the caller to pass full
 * candidate objects) mirrors how a real endpoint would look them up server-side from an id list.
 *
 * A resubmission (this report already carries a `qa` record from a prior round returned for
 * correction) bumps `reportVersion` and starts the checklist and QA result fresh — an earlier
 * version regenerated the digest but left the previous round's checklist answers and Fail record
 * in place, so the reviewer's second pass silently inherited a stale, already-failed result
 * instead of reviewing the corrected content on its own terms. */
export async function submitReportForQa(
  report: DailyBriefReport,
  options: { signal?: AbortSignal } = {},
): Promise<DailyBriefReport> {
  const errors = validateBrief(report)
  if (errors.length > 0) {
    throw new ReportsApiError(`Report is not ready for QA: ${errors[0]}`)
  }
  if (report.state !== 'Report Drafted') {
    throw new ReportsApiError(`Cannot submit for QA from state "${report.state}".`)
  }
  await delay(SIMULATED_LATENCY_MS, options.signal)
  const selectedCandidates = candidatesFixture().filter((candidate) =>
    report.selectedCandidateIds.includes(candidate.id),
  )
  const isResubmission = report.qa !== null
  return {
    ...report,
    ...generatedDigestContent(selectedCandidates),
    state: 'QA In Progress',
    generatedAt: report.generatedAt || new Date().toISOString(),
    reportVersion: isResubmission ? bumpReportVersion(report.reportVersion) : report.reportVersion,
    qaChecklist: isResubmission ? qaChecklistFixture() : report.qaChecklist,
    qa: isResubmission ? null : report.qa,
  }
}

/** POST /api/reports/:id/qa — records the SIP-188 result; Critical fail routes to QA Failed.
 *
 * Fails closed on three paths that previously reached `Awaiting CEO Decision` with a `Pass`:
 * a blank reviewer (the `reviewer &&` guard below made the analyst-check a no-op for one), an
 * empty or malformed checklist (nothing to disprove a pass), and `na` on a Critical item (not a
 * recorded Fail, so it slipped past the Critical-fail check entirely). None of SIP-188's Critical
 * items (a2, b2, c3, d4, e1 in lib/fixtures.ts) describe a check that can legitimately not apply
 * to a run, so Critical + `na` is treated as a failure rather than invented as a fourth outcome. */
export async function submitQaResult(
  report: DailyBriefReport,
  checklist: QaChecklistGroup[],
  reviewer: string,
  options: { signal?: AbortSignal } = {},
): Promise<DailyBriefReport> {
  if (report.state !== 'QA In Progress') {
    throw new ReportsApiError(`Cannot record a QA result from state "${report.state}".`)
  }
  if (!reviewer.trim()) {
    throw new ReportsApiError('A reviewer is required to record a QA result.')
  }
  // The UI's job is to make the illegal path (reviewer === analyst) impossible to reach, not to
  // be the only thing preventing it (docs/sip-ui-spec.md) — re-checked here too, fail-closed.
  if (reviewer === report.analyst) {
    throw new ReportsApiError('The reviewer cannot be this run\'s analyst.')
  }
  const allItems = checklist.flatMap((group) => group.items)
  if (allItems.length === 0) {
    throw new ReportsApiError('The QA checklist is empty — nothing has been reviewed.')
  }
  await delay(SIMULATED_LATENCY_MS, options.signal)

  const isCriticalFailure = (item: QaChecklistGroup['items'][number]) =>
    item.critical && (item.answer === 'fail' || item.answer === 'na')
  const hasCriticalFail = allItems.some(isCriticalFailure)
  const anyUnanswered = allItems.some((item) => item.answer === null)
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
        ? allItems
            .filter(isCriticalFailure)
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
  // Fail-closed re-check of the same required fields CeoDecisionScreen's disabled-button gate
  // enforces (`conditions` is the one genuinely optional field, per its "if any" label) — an
  // earlier version only checked `decision` here, so a caller bypassing the UI could record a
  // decision with a blank reason, owner, evidence reference, next review date or version, or a
  // null timestamp.
  if (!decision.reportVersion.trim()) {
    throw new ReportsApiError('A report version is required.')
  }
  if (!decision.reason.trim()) {
    throw new ReportsApiError('A reason is required.')
  }
  if (!decision.owner.trim()) {
    throw new ReportsApiError('An owner is required.')
  }
  if (!decision.evidenceReference.trim()) {
    throw new ReportsApiError('An evidence reference is required.')
  }
  if (!decision.nextReviewDate.trim()) {
    throw new ReportsApiError('A next review date is required.')
  }
  if (!decision.decidedAt) {
    throw new ReportsApiError('A decision timestamp is required.')
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
