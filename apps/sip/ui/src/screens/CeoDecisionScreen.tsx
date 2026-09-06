import { useEffect, useId, useRef, useState } from 'react'
import {
  authoriseDistribution,
  fetchDistributionReadiness,
  recordCeoDecision,
  ReportsApiError,
} from '../api/reportsStore'
import { GOVERNANCE_LINE, type DailyBriefReport, type ReportDecisionType } from '../domain'

/**
 * docs/sip-ui-spec.md Screen 3: "Nothing in this screen, or anywhere in this UI, offers a 'send'
 * action." The modal exists to make authorising distribution a deliberate, confirmed act — not to
 * imply it triggers a send. "No" doesn't get the same ceremony: the spec is explicit that
 * declining is "a valid, complete outcome," and gating the safe default behind a confirmation
 * step would misrepresent it as risky.
 */
function AuthoriseDistributionModal({ onConfirm, onCancel }: { onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="authorise-distribution-title"
        className="w-full max-w-md rounded-md bg-white p-4 shadow-lg"
      >
        <h3 id="authorise-distribution-title" className="text-sm font-semibold text-inzbc-navy">
          Authorise distribution?
        </h3>
        <p className="mt-2 text-sm text-slate-600">
          This records distribution authorisation against the current report version. It does not
          send anything — manual send happens outside this application
          (docs/sip/operator-guide.md Step 13).
        </p>
        {/* Recipient and launch-control state, sourced from docs/sip/launch/launch-config.md —
            an earlier version of this modal showed neither, so the CEO was asked to confirm
            "authorise distribution" with nothing on screen naming who that goes to or confirming
            every automated channel is still off. */}
        <dl className="mt-3 space-y-1 rounded-md border border-inzbc-navy/10 bg-inzbc-navy/5 p-2 text-xs text-inzbc-navy">
          <div>
            <dt className="inline font-semibold">Authorised recipient: </dt>
            <dd className="inline">Sunil Kaushal, sunilkaushalnz@gmail.com (manual email only)</dd>
          </div>
          <div>
            <dt className="inline font-semibold">Automated distribution channels: </dt>
            <dd className="inline">all disabled (email, member, external, website, social)</dd>
          </div>
        </dl>
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-inzbc-navy/20 px-3 py-2 text-sm font-medium text-inzbc-navy transition-colors hover:border-inzbc-navy hover:bg-inzbc-navy/5"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-md bg-inzbc-forest px-3 py-2 text-sm font-semibold text-white"
          >
            Confirm authorisation
          </button>
        </div>
      </div>
    </div>
  )
}

interface Props {
  report: DailyBriefReport
  onChange: (report: DailyBriefReport) => void
}

type SubmitState = { kind: 'idle' } | { kind: 'loading' } | { kind: 'error'; message: string }

// docs/sip-ui-spec.md Screen 3: reachable once QA has passed (Awaiting CEO Decision), and stays
// reachable through this screen's own outcomes so the CEO can complete the separate distribution
// step and anyone can see what was decided — but never from an earlier, undecided state.
const REACHABLE_STATES: DailyBriefReport['state'][] = [
  'Awaiting CEO Decision',
  'Continue',
  'Continue With Correction',
  'Paused',
  'Stopped',
  'Approved for Manual Distribution',
]

const DECISION_OPTIONS: { value: ReportDecisionType; label: string; tone: 'approve' | 'reject' }[] = [
  { value: 'continue', label: 'Continue', tone: 'approve' },
  { value: 'continue_with_correction', label: 'Continue With Correction', tone: 'reject' },
  { value: 'pause', label: 'Pause', tone: 'reject' },
  { value: 'stop', label: 'Stop', tone: 'reject' },
]

/**
 * docs/sip-ui-spec.md Screen 3: "Two separate, sequential decisions — never presented as one
 * combined control." This screen covers the first of those two: picking a report decision
 * (Continue / Continue With Correction / Pause / Stop) and recording it with the reason,
 * conditions, owner, evidence reference and next review date the spec requires before it can be
 * submitted. The second, separate action — distribution authorisation — only becomes available
 * after this one is recorded (see the Continue/Continue With Correction branch below and
 * `authoriseDistribution` in reportsStore.ts). Both this screen's decision and that one stay
 * fixture-backed — no HTTP route is mounted for either, pending ADR-0005's client decision on
 * who may approve what (see reportsStore.ts's doc comment on `recordCeoDecision`) — and this
 * submit deliberately has no path back into it either way.
 *
 * Unlike QaReviewScreen, this screen has no role gate at all — anyone with a report in
 * `Awaiting CEO Decision` can record its decision, regardless of who they are. QaReviewScreen's
 * own gate (`report.reviewer` standing in for the authenticated session) is itself only a partial
 * answer, since there is no live auth yet (docs/api-integration-spec.md) to check that stand-in
 * against. Adding an equivalent check here would mean inventing a "current user" concept with
 * nothing real behind it — that's issue #42 (auth and role model), not something to fake in a UI
 * spec-fixture screen.
 */
export function CeoDecisionScreen({ report, onChange }: Props) {
  const [selectedDecision, setSelectedDecision] = useState<ReportDecisionType | null>(null)
  const [reason, setReason] = useState('')
  const [conditions, setConditions] = useState('')
  const [owner, setOwner] = useState('')
  const [evidenceReference, setEvidenceReference] = useState('')
  const [nextReviewDate, setNextReviewDate] = useState('')
  const [submitState, setSubmitState] = useState<SubmitState>({ kind: 'idle' })
  const [distributionState, setDistributionState] = useState<SubmitState>({ kind: 'idle' })
  const [confirmingDistribution, setConfirmingDistribution] = useState(false)
  // Which report version + state the `ready` value was actually fetched for, alongside the value
  // itself — both in state (not a ref) because render needs to read the pairing to tell a fresh
  // answer from a stale one, and a ref's `.current` may not be read during render. A mismatch (or
  // no result yet) reads as `null`: unknown, loading, or a failed check all fail closed the same
  // way an absent redaction policy or missing API key refuses rather than assumes.
  const [distributionReadiness, setDistributionReadiness] = useState<{
    identity: string
    ready: boolean
  } | null>(null)
  const inFlight = useRef<AbortController | null>(null)
  const distributionInFlight = useRef<AbortController | null>(null)
  // One key per submission attempt, not per call: services/api's `_DecisionIn.idempotency_key` is
  // caller-supplied so a retry of the same click can be deduplicated against the first attempt
  // rather than recorded as a second decision (reportsStore.ts's `recordCeoDecision` doc comment).
  // Cleared on success and whenever the underlying choice changes, since that is a new intent, not
  // a retry of the old one.
  const rulingIdempotencyKey = useRef<string | null>(null)
  const distributionIdempotencyKey = useRef<string | null>(null)
  const reasonId = useId()
  const conditionsId = useId()
  const ownerId = useId()
  const ownerHintId = useId()
  const evidenceId = useId()
  const nextReviewId = useId()

  const distributionIdentity =
    report.state === 'Continue' && report.decision && !report.decision.distributionDecidedAt
      ? report.reportVersionId
      : null

  // Checked only for `Continue`: `Continue With Correction` can never be authorised regardless of
  // approval state (ADR-0005), so there's nothing useful to fetch for it. setDistributionReadiness
  // is called only from the async callbacks below, never synchronously in the effect body.
  useEffect(() => {
    if (!distributionIdentity) return
    const identity = distributionIdentity
    const controller = new AbortController()
    fetchDistributionReadiness(identity, { signal: controller.signal })
      .then((ready) => {
        if (!controller.signal.aborted) setDistributionReadiness({ identity, ready })
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        // Fail closed: an unknown readiness state disables the control — the ambiguity should
        // never read as permission.
        if (!controller.signal.aborted) setDistributionReadiness({ identity, ready: false })
      })
    return () => controller.abort()
  }, [distributionIdentity])

  const effectiveDistributionReady =
    distributionReadiness?.identity === distributionIdentity ? distributionReadiness.ready : null

  const missingFields: string[] = []
  if (selectedDecision) {
    if (!reason.trim()) missingFields.push('reason')
    if (!owner.trim()) missingFields.push('owner')
    if (!evidenceReference.trim()) missingFields.push('evidence reference')
    if (!nextReviewDate.trim()) missingFields.push('next review date')
  }
  const canSubmit = selectedDecision !== null && missingFields.length === 0

  async function onSubmitDecision() {
    if (!canSubmit || !selectedDecision) return
    inFlight.current?.abort()
    const controller = new AbortController()
    inFlight.current = controller
    // Generated once per decision, reused on every retry of it — a lost response and a resend of
    // the same click must reach the server as the same act, not a second one.
    rulingIdempotencyKey.current ??= crypto.randomUUID()
    setSubmitState({ kind: 'loading' })
    try {
      const updated = await recordCeoDecision(
        report,
        {
          reportVersion: report.reportVersion,
          decision: selectedDecision,
          reason: reason.trim(),
          conditions: conditions.trim(),
          owner: owner.trim(),
          evidenceReference: evidenceReference.trim(),
          nextReviewDate,
          decidedAt: new Date().toISOString(),
        },
        { signal: controller.signal, idempotencyKey: rulingIdempotencyKey.current },
      )
      if (inFlight.current !== controller) return
      rulingIdempotencyKey.current = null
      setSubmitState({ kind: 'idle' })
      onChange(updated)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      if (inFlight.current !== controller) return
      setSubmitState({
        kind: 'error',
        message: error instanceof ReportsApiError ? error.message : 'Something went wrong. Please try again.',
      })
    }
  }

  async function onAuthoriseDistribution(authorised: boolean) {
    distributionInFlight.current?.abort()
    const controller = new AbortController()
    distributionInFlight.current = controller
    distributionIdempotencyKey.current ??= crypto.randomUUID()
    setDistributionState({ kind: 'loading' })
    try {
      const updated = await authoriseDistribution(report, authorised, {
        signal: controller.signal,
        idempotencyKey: distributionIdempotencyKey.current,
      })
      if (distributionInFlight.current !== controller) return
      distributionIdempotencyKey.current = null
      setDistributionState({ kind: 'idle' })
      setConfirmingDistribution(false)
      onChange(updated)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      if (distributionInFlight.current !== controller) return
      setConfirmingDistribution(false)
      setDistributionState({
        kind: 'error',
        message: error instanceof ReportsApiError ? error.message : 'Something went wrong. Please try again.',
      })
    }
  }

  if (!REACHABLE_STATES.includes(report.state)) {
    return (
      <section>
        <h2 className="text-lg font-semibold text-inzbc-navy">CEO Decision</h2>
        <p role="status" className="mt-2 text-sm text-slate-600">
          Not reachable yet — this run is currently <strong>{report.state}</strong>. The CEO
          decision opens once QA has passed (QA In Progress → Awaiting CEO Decision).
        </p>
      </section>
    )
  }

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-inzbc-navy">CEO Decision</h2>
        <p className="mt-1 text-sm text-slate-600">
          Deciding against report version <strong>{report.reportVersion}</strong>. Run: {report.runId}.
          Built against controlling documents {report.approvedVersionSet}.
        </p>
        <p className="mt-2 rounded-md border border-inzbc-navy/20 bg-inzbc-navy/5 p-2 text-xs font-medium text-inzbc-navy">
          {GOVERNANCE_LINE}
        </p>
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-inzbc-navy">Digest preview</h3>
        {report.sections.map((section) => (
          <div key={section.id} className="rounded-md border border-inzbc-navy/10 bg-white shadow-sm p-3">
            <h4 className="text-sm font-medium text-inzbc-navy">{section.title}</h4>
            <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
              {section.content || <span className="italic text-slate-600">No content recorded.</span>}
            </p>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-inzbc-navy">7. CEO action list</h3>
        {report.ceoActionList.length === 0 ? (
          <p className="text-sm text-slate-500">No CEO actions recorded for this run.</p>
        ) : (
          report.ceoActionList.map((action) => (
            <div key={action.id} className="rounded-md border border-inzbc-navy/10 bg-white shadow-sm p-3 text-sm">
              <p className="text-slate-700">{action.action}</p>
              <p className="mt-1 text-xs text-slate-500">
                Owner: {action.owner} · Priority: {action.priority} · Due: {action.dueDate}
              </p>
            </div>
          ))
        )}
      </div>

      {report.state === 'Awaiting CEO Decision' ? (
        <div className="space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-inzbc-navy">Report decision</h3>
            <div role="radiogroup" aria-label="Report decision" className="mt-2 flex flex-wrap gap-2">
              {DECISION_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={selectedDecision === option.value}
                  onClick={() => {
                    // A different decision is a new intent, not a retry of the old one — an
                    // abandoned Stop attempt's key must never be reused for a Continue.
                    rulingIdempotencyKey.current = null
                    setSelectedDecision(option.value)
                  }}
                  className={`rounded-md border px-3 py-2 text-sm font-medium ${
                    selectedDecision === option.value
                      ? option.tone === 'approve'
                        ? 'border-inzbc-forest bg-inzbc-forest text-white'
                        : 'border-inzbc-crimson bg-inzbc-crimson text-white'
                      : 'border-inzbc-navy/20 text-inzbc-navy'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {selectedDecision ? (
            <div className="space-y-3 rounded-md border border-inzbc-navy/10 bg-white shadow-sm p-3">
              <div>
                <label htmlFor={reasonId} className="block text-xs font-medium text-inzbc-navy">
                  Reason
                </label>
                <textarea
                  id={reasonId}
                  className="mt-1 min-h-16 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                />
              </div>
              <div>
                <label htmlFor={conditionsId} className="block text-xs font-medium text-inzbc-navy">
                  Conditions (if any)
                </label>
                <textarea
                  id={conditionsId}
                  className="mt-1 min-h-12 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                  value={conditions}
                  onChange={(event) => setConditions(event.target.value)}
                />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label htmlFor={ownerId} className="block text-xs font-medium text-inzbc-navy">
                    Owner (display only)
                  </label>
                  <input
                    id={ownerId}
                    type="text"
                    aria-describedby={ownerHintId}
                    className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                    value={owner}
                    onChange={(event) => setOwner(event.target.value)}
                  />
                  {/* services/api's decision_records.owner_id is a real users.id FK with no
                      user-directory endpoint yet to resolve free text against (reportsStore.ts's
                      recordCeoDecision doc comment) — the signed-in account is what's actually
                      recorded, not this field. Said here rather than left implicit, so what's on
                      screen doesn't disagree with what's in the audit record. */}
                  <p id={ownerHintId} className="mt-1 text-xs text-slate-500">
                    Shown here for context only — the decision is recorded against your signed-in
                    account, not this text.
                  </p>
                </div>
                <div>
                  <label htmlFor={evidenceId} className="block text-xs font-medium text-inzbc-navy">
                    Evidence reference
                  </label>
                  <input
                    id={evidenceId}
                    type="text"
                    className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                    value={evidenceReference}
                    onChange={(event) => setEvidenceReference(event.target.value)}
                  />
                </div>
              </div>
              <div>
                <label htmlFor={nextReviewId} className="block text-xs font-medium text-inzbc-navy">
                  Next review date
                </label>
                <input
                  id={nextReviewId}
                  type="date"
                  className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue sm:w-auto"
                  value={nextReviewDate}
                  onChange={(event) => setNextReviewDate(event.target.value)}
                />
              </div>

              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => void onSubmitDecision()}
                  disabled={!canSubmit || submitState.kind === 'loading'}
                  className="rounded-md bg-inzbc-tangerine px-4 py-2 font-semibold text-inzbc-navy transition-colors hover:enabled:bg-inzbc-tangerine/90 disabled:cursor-progress disabled:opacity-60"
                >
                  {submitState.kind === 'loading' ? 'Recording…' : 'Record decision'}
                </button>
                {missingFields.length > 0 ? (
                  <p role="alert" className="text-xs text-inzbc-crimson">
                    Still required: {missingFields.join(', ')}.
                  </p>
                ) : null}
                {submitState.kind === 'error' ? (
                  <p role="alert" className="text-sm text-inzbc-crimson">
                    {submitState.message}
                  </p>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <div className="space-y-3">
          <p role="status" className="text-sm text-slate-600">
            Report decision already recorded: <strong>{report.decision?.decision ?? report.state}</strong>.
          </p>

          {/* docs/sip-ui-spec.md: distribution authorisation is reachable only from Continue /
              Continue With Correction — a Paused or Stopped run never reaches this question, and
              once decided it isn't offered again (distributionDecidedAt is set). */}
          {(report.state === 'Continue' || report.state === 'Continue With Correction') &&
          report.decision &&
          !report.decision.distributionDecidedAt ? (
            <div className="space-y-2 rounded-md border border-inzbc-navy/10 bg-white shadow-sm p-3">
              <h3 className="text-sm font-semibold text-inzbc-navy">Authorise distribution</h3>
              <p className="text-xs text-slate-500">
                A second, independent decision — approving the report is not permission to send.
              </p>
              {/* ADR-0005/REQ-G-04 (services/api/decisions.py's `record()`) accepts `Authorised`
                  only when the ruling is exactly `Continue` — never `Continue With Correction`,
                  since a corrected version needs its own fresh approval and authority decision.
                  Refusing this control from the state that can never succeed, rather than letting
                  the person click into a guaranteed 422, matches `authoriseDistribution`'s own
                  client-side refusal in reportsStore.ts. */}
              {report.state === 'Continue With Correction' ? (
                <p className="text-xs text-slate-500">
                  Authorisation is not available for a corrected version — it needs its own fresh
                  report approval first. Record "No" to refuse explicitly, or wait for the fresh
                  approval on the corrected version.
                </p>
              ) : null}
              <div className="flex gap-2">
                {report.state === 'Continue' ? (
                  <button
                    type="button"
                    onClick={() => setConfirmingDistribution(true)}
                    disabled={
                      distributionState.kind === 'loading' || effectiveDistributionReady !== true
                    }
                    title={
                      effectiveDistributionReady === false
                        ? 'Not yet authorisable: the report approval is not recorded as Approved.'
                        : undefined
                    }
                    className="rounded-md bg-inzbc-forest px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Yes, authorise
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => void onAuthoriseDistribution(false)}
                  disabled={distributionState.kind === 'loading'}
                  className="rounded-md border border-inzbc-navy/20 px-3 py-2 text-sm font-medium text-inzbc-navy transition-colors hover:enabled:border-inzbc-navy hover:enabled:bg-inzbc-navy/5 disabled:cursor-progress disabled:opacity-60"
                >
                  No
                </button>
              </div>
              {/* `report_approval` has no UI anywhere yet (reportsStore.ts's `recordCeoDecision`
                  doc comment) — until something else records it, this stays false in the
                  ordinary flow, and that is accurate, not a bug in this check. */}
              {report.state === 'Continue' && effectiveDistributionReady === false ? (
                <p role="status" className="text-xs text-slate-500">
                  Waiting on report approval before distribution can be authorised.
                </p>
              ) : null}
              {distributionState.kind === 'error' ? (
                <p role="alert" className="text-sm text-inzbc-crimson">
                  {distributionState.message}
                </p>
              ) : null}
            </div>
          ) : null}

          {report.decision?.distributionDecidedAt ? (
            <p className="text-sm text-slate-600">
              Distribution authorised:{' '}
              <strong>{report.decision.distributionAuthorised ? 'Yes' : 'No'}</strong>.
            </p>
          ) : null}
        </div>
      )}

      {confirmingDistribution ? (
        <AuthoriseDistributionModal
          onConfirm={() => void onAuthoriseDistribution(true)}
          onCancel={() => setConfirmingDistribution(false)}
        />
      ) : null}
    </section>
  )
}
