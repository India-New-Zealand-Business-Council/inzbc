import type { CeoDecisionRecord, DailyBriefReport, QaChecklistGroup, ReportDecisionType } from '../domain'
import { candidatesFixture, generatedDigestContent, qaChecklistFixture } from '../lib/fixtures'
import { validateBrief } from '../lib/validation'
import { getCsrfToken } from './session'

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
 * `POST /api/reports`, `POST /api/reports/{id}/qa` and `POST /api/runs/{id}/fail-qa` are live
 * (#124, #285) and `submitReportForQa`/`submitQaResult` below call them for real — issue #336.
 * `returnForCorrection`, `recordCeoDecision` and `authoriseDistribution` stay fixture-backed:
 * there is no HTTP route for any of the three, for two different reasons documented at each
 * function below, not because nobody got to them yet.
 *
 * Every real call needs `credentials: 'same-origin'` plus an `X-CSRF-Token` header fetched from
 * `GET /api/session` first — the same pattern apps/comms/ui/src/api/client.ts already proved,
 * reused via ./session rather than reinvented.
 */

const JSON_HEADERS = { 'Content-Type': 'application/json', Accept: 'application/json' } as const

/** Extracts FastAPI's standard `{"detail": "..."}` shape when present, so a 403/409/422 reaches
 * the user as the server's own explanation (a self-review refusal, a stale version) rather than a
 * bare status code. Falls back to the status code when the body isn't in that shape or can't be
 * parsed at all — still fails closed, just with less to say. */
async function errorFromResponse(response: Response, fallback: string): Promise<ReportsApiError> {
  try {
    const body: unknown = await response.json()
    if (body && typeof body === 'object' && typeof (body as { detail?: unknown }).detail === 'string') {
      return new ReportsApiError((body as { detail: string }).detail)
    }
  } catch {
    // Body wasn't JSON, or wasn't readable — the fallback below still says something.
  }
  return new ReportsApiError(`${fallback} (${response.status}).`)
}

async function authedFetch(
  url: string,
  init: { method: 'POST'; body: unknown; signal?: AbortSignal },
): Promise<Response> {
  const csrfToken = await getCsrfToken()
  return fetch(url, {
    method: init.method,
    signal: init.signal,
    credentials: 'same-origin',
    headers: { ...JSON_HEADERS, 'X-CSRF-Token': csrfToken },
    body: JSON.stringify(init.body),
  })
}

/** Lowercase hex SHA-256, matching `SubmitReportIn.content_sha256`'s `^[0-9a-f]{64}$` pattern.
 * Hashes the generated digest content, not the whole report object — fields like `focusNote` or
 * `selectedCandidateIds` describe how the brief was assembled, not what's in it; hashing the
 * assembled output is what makes "the thing approved is the thing distributed" checkable. */
async function sha256Hex(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
}

interface ReportVersionOut {
  id: string
  run_id: string
  version_number: number
  created_by: string
  content_sha256: string
  created_at: string
  submitted_at: string
}

/** POST /api/reports/:id/submit — Report Drafted -> QA In Progress.
 *
 * Client-side validation stays exactly as it was: `SubmitReportIn` carries only a run id, a
 * content hash and a timestamp, so the server has nothing to check the brief's actual content
 * against — this check is the only one that exists, not a redundant mirror of a server-side rule.
 *
 * Real versioning replaces the old client-side `bumpReportVersion` — `POST /api/reports` assigns
 * `version_number` itself (`services/api/reports.py`: "not by the caller"), so a resubmission's
 * next version number comes from the response, not from incrementing a string here. The checklist
 * and prior QA result still reset locally on a resubmission (`report.qa !== null`), since that's
 * this UI's own behaviour, not the server's — a reviewer's second pass should review the corrected
 * content on its own terms rather than inherit a stale, already-failed result.
 *
 * **Known gap, found by manual testing against a real backend, not yet fixed:** `report.runId`
 * comes from `newDraftReportFixture()` as a human-readable run number (`'RUN-20260730-01'`), but
 * `SubmitReportIn.run_id` is validated server-side as a UUID (`runs.id`) — a run number is not
 * accepted and this call 500s (`psycopg.errors.InvalidTextRepresentation`). Nothing in the SIP UI
 * ever calls `GET /api/runs` to obtain a real one, so this can't be fixed inside this function — it
 * needs the SIP UI to actually select a real run first, which is bigger than #336's scope (wiring
 * the report/QA actions to endpoints that already exist). Left as a known limitation rather than a
 * silent one; a run-selection screen is the real fix.
 */
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
  const selectedCandidates = candidatesFixture().filter((candidate) =>
    report.selectedCandidateIds.includes(candidate.id),
  )
  const digest = generatedDigestContent(selectedCandidates)
  const contentSha256 = await sha256Hex(JSON.stringify(digest))
  const createdAt = new Date().toISOString()

  let response: Response
  try {
    response = await authedFetch('/api/reports', {
      method: 'POST',
      signal: options.signal,
      body: { run_id: report.runId, content_sha256: contentSha256, created_at: createdAt },
    })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new ReportsApiError('Could not reach the reports service.', { cause })
  }
  if (!response.ok) {
    throw await errorFromResponse(response, 'Submitting the report for QA failed')
  }
  const version = (await response.json()) as ReportVersionOut

  const isResubmission = report.qa !== null
  return {
    ...report,
    ...digest,
    state: 'QA In Progress',
    generatedAt: report.generatedAt || createdAt,
    reportVersion: `v${version.version_number}`,
    reportVersionId: version.id,
    qaChecklist: isResubmission ? qaChecklistFixture() : report.qaChecklist,
    qa: isResubmission ? null : report.qa,
  }
}

interface QaResultOut {
  report_version_id: string
  qa_status: string
  critical_failures: number
}

interface RunOut {
  id: string
  state: string
  version: number
}

/** POST /api/reports/:id/qa — records the SIP-188 result, then, on a Fail, calls
 * `POST /api/runs/:id/fail-qa` to actually stop the run.
 *
 * Two calls, not one, because they're two different acts (`services/api/reports.py`'s own
 * docstring on `record_qa`): recording a result is the reviewer's finding; failing the run is the
 * reviewer's independent lifecycle authority (REQ-U-01) and needs the run's `expected_version` so
 * a stale transition is refused rather than silently applied. `report.runVersion` carries that;
 * it's bumped here from the `fail-qa` response so the next transition this report attempts has
 * the version the server just wrote, not the one it started this call with.
 *
 * `notes` is new here — `RecordQaIn.notes` is required server-side (min length 1) and this
 * fixture never collected it, because nothing consumed it. QaReviewScreen now has a field for it. */
export async function submitQaResult(
  report: DailyBriefReport,
  checklist: QaChecklistGroup[],
  reviewer: string,
  notes: string,
  options: { signal?: AbortSignal } = {},
): Promise<DailyBriefReport> {
  if (report.state !== 'QA In Progress') {
    throw new ReportsApiError(`Cannot record a QA result from state "${report.state}".`)
  }
  if (!reviewer.trim()) {
    throw new ReportsApiError('A reviewer is required to record a QA result.')
  }
  if (reviewer === report.analyst) {
    throw new ReportsApiError('The reviewer cannot be this run\'s analyst.')
  }
  const allItems = checklist.flatMap((group) => group.items)
  if (allItems.length === 0) {
    throw new ReportsApiError('The QA checklist is empty — nothing has been reviewed.')
  }
  if (!notes.trim()) {
    throw new ReportsApiError('QA notes are required to record a result.')
  }
  if (!report.reportVersionId) {
    throw new ReportsApiError('This report has not been submitted yet — nothing to record QA against.')
  }

  const isCriticalFailure = (item: QaChecklistGroup['items'][number]) =>
    item.critical && (item.answer === 'fail' || item.answer === 'na')
  const hasCriticalFail = allItems.some(isCriticalFailure)
  const anyUnanswered = allItems.some((item) => item.answer === null)
  const passed = !hasCriticalFail && !anyUnanswered
  const criticalFailuresFound = hasCriticalFail
    ? allItems
        .filter(isCriticalFailure)
        .map((item) => item.text)
        .join('; ')
    : ''

  let qaResponse: Response
  try {
    qaResponse = await authedFetch(`/api/reports/${encodeURIComponent(report.reportVersionId)}/qa`, {
      method: 'POST',
      signal: options.signal,
      body: {
        result: passed ? 'Pass' : 'Fail',
        critical_failures: hasCriticalFail ? allItems.filter(isCriticalFailure).length : 0,
        notes: notes.trim(),
      },
    })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new ReportsApiError('Could not reach the reports service.', { cause })
  }
  if (!qaResponse.ok) {
    throw await errorFromResponse(qaResponse, 'Recording the QA result failed')
  }
  await (qaResponse.json() as Promise<QaResultOut>) // consumed for its status code; nothing here changes the local view beyond what's built below.

  let runVersion = report.runVersion
  if (!passed) {
    let runResponse: Response
    try {
      runResponse = await authedFetch(`/api/runs/${encodeURIComponent(report.runId)}/fail-qa`, {
        method: 'POST',
        signal: options.signal,
        body: {
          expected_version: report.runVersion,
          reason: criticalFailuresFound || 'QA checklist not fully passed.',
          approval_ref: null,
        },
      })
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
      throw new ReportsApiError('Recorded the QA result, but could not reach the run service to stop the run.', {
        cause,
      })
    }
    if (!runResponse.ok) {
      throw await errorFromResponse(
        runResponse,
        'The QA result was recorded, but stopping the run failed',
      )
    }
    const run = (await runResponse.json()) as RunOut
    runVersion = run.version
  }

  return {
    ...report,
    qaChecklist: checklist,
    state: passed ? 'Awaiting CEO Decision' : 'QA Failed',
    runVersion,
    qa: {
      reviewer,
      timestamp: new Date().toISOString(),
      result: passed ? 'Pass' : 'Fail',
      criticalFailuresFound,
      correctionsRequired: passed ? '' : 'See flagged Critical items above.',
    },
  }
}

/**
 * QA Failed -> Report Drafted — **no live endpoint**, and not for the same reason as the two
 * decision functions below.
 *
 * `services/api/runs.py`'s own module docstring draws the line: `start`/`pause`/`resume`/
 * `fail-qa`/`stop`/`complete` are "the one HTTP-triggered move" in their edge's position — the
 * mechanical steps in between, including Report Drafted, are "driven by the pipeline/agent loop
 * ... not this router." A human sending a run from QA Failed back to Report Drafted isn't one of
 * this router's edges; the correction itself (editing the digest, per this screen) is manual, but
 * re-entering Report Drafted is not a control a person exercises over HTTP today. Stays
 * fixture-backed until that's built, which is separate work from wiring the calls that do exist.
 */
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
 * **No live endpoint, and this is a client decision pending, not an engineering gap.**
 * `services/api/reports.py`'s own docstring: "The decision-writing endpoints are deliberately
 * absent ... `decision_role_permissions` is unseeded: no row means nobody may act ... Mounting
 * them now would ship three endpoints that answer 403 until INZBC decides who may approve what."
 * Tracked as ADR-0005 required follow-up 4 / client answers B8. Stays fixture-backed until INZBC
 * answers who may record a CEO ruling, report approval and distribution authority — wiring this
 * function to a 403-only endpoint would not make the screen more real, only slower to fail.
 *
 * docs/sip-ui-spec.md Screen 3: "Two separate, sequential decisions — never presented as one
 * combined control ... The UI must not let the CEO set [distribution authorisation] in the same
 * submit as decision 1." The parameter type excludes those fields outright so the two decisions
 * can't be recombined by a future caller either. `authoriseDistribution` below is the separate,
 * second action.
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
 * Same "no live endpoint" reason as `recordCeoDecision` immediately above — see that function's
 * doc comment. Only reachable once a report decision is already recorded, and only from the two
 * states a distribution question is meaningful for (`Continue` / `Continue With Correction`) — a
 * Paused or Stopped run doesn't reach this question. `authorised: false` is a complete, valid
 * outcome (docs/sip-ui-spec.md: "not an error or incomplete state") — the run simply stays in its
 * current state, proceeding to close-out with distribution skipped, rather than needing a further
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
