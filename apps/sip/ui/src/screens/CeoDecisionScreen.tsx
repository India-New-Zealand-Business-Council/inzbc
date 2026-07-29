import { useId, useRef, useState } from 'react'
import { recordCeoDecision, ReportsApiError } from '../api/reportsStore'
import { GOVERNANCE_LINE, type DailyBriefReport, type ReportDecisionType } from '../domain'

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
 * `authoriseDistribution` in reportsStore.ts) and is wired in a later commit; it deliberately has
 * no path back into this same submit.
 */
export function CeoDecisionScreen({ report, onChange }: Props) {
  const [selectedDecision, setSelectedDecision] = useState<ReportDecisionType | null>(null)
  const [reason, setReason] = useState('')
  const [conditions, setConditions] = useState('')
  const [owner, setOwner] = useState('')
  const [evidenceReference, setEvidenceReference] = useState('')
  const [nextReviewDate, setNextReviewDate] = useState('')
  const [submitState, setSubmitState] = useState<SubmitState>({ kind: 'idle' })
  const inFlight = useRef<AbortController | null>(null)
  const reasonId = useId()
  const conditionsId = useId()
  const ownerId = useId()
  const evidenceId = useId()
  const nextReviewId = useId()

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
    setSubmitState({ kind: 'loading' })
    try {
      const updated = await recordCeoDecision(
        report,
        {
          reportVersion: report.approvedVersionSet,
          decision: selectedDecision,
          reason: reason.trim(),
          conditions: conditions.trim(),
          owner: owner.trim(),
          evidenceReference: evidenceReference.trim(),
          nextReviewDate,
          decidedAt: new Date().toISOString(),
        },
        { signal: controller.signal },
      )
      if (inFlight.current !== controller) return
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
          Deciding against version <strong>{report.approvedVersionSet}</strong>. Run: {report.runId}.
        </p>
        <p className="mt-2 rounded-md border border-inzbc-navy/20 bg-inzbc-navy/5 p-2 text-xs font-medium text-inzbc-navy">
          {GOVERNANCE_LINE}
        </p>
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-inzbc-navy">Digest preview</h3>
        {report.sections.map((section) => (
          <div key={section.id} className="rounded-md border border-slate-200 bg-white p-3">
            <h4 className="text-sm font-medium text-inzbc-navy">{section.title}</h4>
            <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
              {section.content || <span className="italic text-slate-400">No content recorded.</span>}
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
            <div key={action.id} className="rounded-md border border-slate-200 bg-white p-3 text-sm">
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
                  onClick={() => setSelectedDecision(option.value)}
                  className={`rounded-md border px-3 py-2 text-sm font-medium ${
                    selectedDecision === option.value
                      ? option.tone === 'approve'
                        ? 'border-inzbc-forest bg-inzbc-forest text-white'
                        : 'border-inzbc-crimson bg-inzbc-crimson text-white'
                      : 'border-slate-300 text-inzbc-navy'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {selectedDecision ? (
            <div className="space-y-3 rounded-md border border-slate-200 bg-white p-3">
              <div>
                <label htmlFor={reasonId} className="block text-xs font-medium text-inzbc-navy">
                  Reason
                </label>
                <textarea
                  id={reasonId}
                  className="mt-1 min-h-16 w-full rounded-md border border-slate-300 p-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
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
                  className="mt-1 min-h-12 w-full rounded-md border border-slate-300 p-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                  value={conditions}
                  onChange={(event) => setConditions(event.target.value)}
                />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label htmlFor={ownerId} className="block text-xs font-medium text-inzbc-navy">
                    Owner
                  </label>
                  <input
                    id={ownerId}
                    type="text"
                    className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                    value={owner}
                    onChange={(event) => setOwner(event.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor={evidenceId} className="block text-xs font-medium text-inzbc-navy">
                    Evidence reference
                  </label>
                  <input
                    id={evidenceId}
                    type="text"
                    className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
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
                  className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue sm:w-auto"
                  value={nextReviewDate}
                  onChange={(event) => setNextReviewDate(event.target.value)}
                />
              </div>

              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => void onSubmitDecision()}
                  disabled={!canSubmit || submitState.kind === 'loading'}
                  className="rounded-md bg-inzbc-tangerine px-4 py-2 font-semibold text-white disabled:cursor-progress disabled:opacity-60"
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
        <p role="status" className="text-sm text-slate-600">
          Report decision already recorded: <strong>{report.decision?.decision ?? report.state}</strong>.
        </p>
      )}
    </section>
  )
}
