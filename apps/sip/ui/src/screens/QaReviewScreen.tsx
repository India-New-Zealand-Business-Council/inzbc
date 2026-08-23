import { useId, useMemo, useRef, useState } from 'react'
import { returnForCorrection, ReportsApiError, submitQaResult } from '../api/reportsStore'
import { GOVERNANCE_LINE, type DailyBriefReport, type QaAnswer, type ReviewStatus } from '../domain'

interface Props {
  report: DailyBriefReport
  onChange: (report: DailyBriefReport) => void
}

// Colour-coded per the brand palette rather than arbitrary colours: forest = approved (same
// "healthy" association as the rest of this UI), crimson = flagged (matches the alert/error
// colour used everywhere else in this component), slate = still pending, nothing decided yet.
const SECTION_CARD_CLASSES: Record<ReviewStatus, string> = {
  pending: 'border-inzbc-navy/10 bg-white',
  approved: 'border-inzbc-forest bg-inzbc-forest/5',
  flagged: 'border-inzbc-crimson bg-inzbc-crimson/5',
}

const QA_ANSWERS: { value: QaAnswer; label: string }[] = [
  { value: 'pass', label: 'Pass' },
  { value: 'fail', label: 'Fail' },
  { value: 'na', label: 'N/A' },
]

type SubmitState = { kind: 'idle' } | { kind: 'loading' } | { kind: 'error'; message: string }

/**
 * docs/sip-ui-spec.md Screen 2, entry condition: "run is in QA In Progress ... if the session's
 * user matches the run's analyst_id, the screen refuses to load and shows why, rather than
 * letting the reviewer start and fail server-side later." There is no live auth yet
 * (docs/api-integration-spec.md), so `report.reviewer` stands in for the authenticated session's
 * identity — the check itself (reviewer !== analyst) is real and matches the server-side rule in
 * schemas/api-contract.md; only the identity source is a stand-in.
 */
export function QaReviewScreen({ report, onChange }: Props) {
  // Which section, if any, is in edit mode — one at a time, so a reviewer can't lose track of an
  // unsaved edit in a section they've scrolled away from.
  const [editingId, setEditingId] = useState<string | null>(null)
  const [submitState, setSubmitState] = useState<SubmitState>({ kind: 'idle' })
  // RecordQaIn.notes is required server-side (min length 1) — this screen never collected it
  // before there was a real endpoint to send it to.
  const [notes, setNotes] = useState('')
  const inFlight = useRef<AbortController | null>(null)
  const editFieldId = useId()
  const notesFieldId = useId()

  const sectionBreakdown = useMemo(() => {
    const approved = report.sections.filter((s) => s.reviewStatus === 'approved').length
    const flagged = report.sections.filter((s) => s.reviewStatus === 'flagged').length
    return { approved, flagged, pending: report.sections.length - approved - flagged, total: report.sections.length }
  }, [report.sections])

  const checklistItems = useMemo(() => report.qaChecklist.flatMap((group) => group.items), [report.qaChecklist])
  const answeredCount = checklistItems.filter((item) => item.answer !== null).length
  const passCount = checklistItems.filter((item) => item.answer === 'pass').length
  const criticalFailCount = checklistItems.filter((item) => item.critical && item.answer === 'fail').length
  // Percentage of *answered* items that passed — an unanswered checklist reads as "0%", not
  // "100% of nothing," which would misrepresent an incomplete review as a clean one.
  const checklistScore = answeredCount === 0 ? 0 : Math.round((passCount / answeredCount) * 100)
  // checklistItems.length > 0 matters on its own: without it, an empty checklist has
  // answeredCount (0) === length (0), satisfying "every item answered" for a checklist that was
  // never actually reviewed.
  const allAnswered = checklistItems.length > 0 && answeredCount === checklistItems.length

  function setChecklistAnswer(groupId: string, itemId: string, answer: QaAnswer) {
    onChange({
      ...report,
      qaChecklist: report.qaChecklist.map((group) =>
        group.id !== groupId
          ? group
          : {
              ...group,
              items: group.items.map((item) =>
                item.id === itemId ? { ...item, answer: item.answer === answer ? null : answer } : item,
              ),
            },
      ),
    })
  }

  async function onRecordResult() {
    if (!allAnswered || !notes.trim()) return
    inFlight.current?.abort()
    const controller = new AbortController()
    inFlight.current = controller
    setSubmitState({ kind: 'loading' })
    try {
      const updated = await submitQaResult(report, report.qaChecklist, report.reviewer, notes, {
        signal: controller.signal,
      })
      if (inFlight.current !== controller) return
      setSubmitState({ kind: 'idle' })
      setNotes('')
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

  async function onSendBackForCorrection() {
    inFlight.current?.abort()
    const controller = new AbortController()
    inFlight.current = controller
    setSubmitState({ kind: 'loading' })
    try {
      const updated = await returnForCorrection(report, { signal: controller.signal })
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

  function updateSectionContent(sectionId: string, content: string) {
    onChange({
      ...report,
      sections: report.sections.map((section) =>
        section.id === sectionId ? { ...section, content } : section,
      ),
    })
  }

  function setSectionReviewStatus(sectionId: string, reviewStatus: ReviewStatus) {
    onChange({
      ...report,
      sections: report.sections.map((section) => {
        if (section.id !== sectionId) return section
        // Clicking the already-active choice clears back to pending rather than being a one-way
        // ratchet; flagReason only makes sense while the section is actually flagged.
        const next = section.reviewStatus === reviewStatus ? 'pending' : reviewStatus
        return { ...section, reviewStatus: next, flagReason: next === 'flagged' ? section.flagReason : '' }
      }),
    })
  }

  function setSectionFlagReason(sectionId: string, flagReason: string) {
    onChange({
      ...report,
      sections: report.sections.map((section) =>
        section.id === sectionId ? { ...section, flagReason } : section,
      ),
    })
  }

  if (report.state !== 'QA In Progress' && report.state !== 'QA Failed') {
    return (
      <section>
        <h2 className="text-lg font-semibold text-inzbc-navy">QA Review</h2>
        <p role="status" className="mt-2 text-sm text-slate-600">
          Not reachable yet — this run is currently <strong>{report.state}</strong>. QA review
          opens once the brief has been submitted (Report Drafted → QA In Progress).
        </p>
      </section>
    )
  }

  if (!report.reviewer.trim()) {
    return (
      <section>
        <h2 className="text-lg font-semibold text-inzbc-navy">QA Review</h2>
        <p role="alert" className="mt-2 text-sm text-inzbc-crimson">
          This screen is blocked: no reviewer is recorded on this run. QA cannot proceed without an
          identified, authenticated reviewer.
        </p>
      </section>
    )
  }

  if (report.reviewer === report.analyst) {
    return (
      <section>
        <h2 className="text-lg font-semibold text-inzbc-navy">QA Review</h2>
        <p role="alert" className="mt-2 text-sm text-inzbc-crimson">
          This screen is blocked: the reviewer on this run ({report.reviewer}) is also its
          analyst. A run's analyst cannot be its own reviewer (schemas/api-contract.md) — assign a
          different reviewer before QA can proceed.
        </p>
      </section>
    )
  }

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-inzbc-navy">QA Review</h2>
        <p className="mt-1 text-sm text-slate-600">
          Independent SIP-188 quality review before this brief reaches the CEO. Reviewer:{' '}
          {report.reviewer}.
        </p>
        {/* docs/sip-ui-spec.md: this line belongs "on every view of the brief, always" — an
            earlier version only rendered it on the CEO decision screen. */}
        <p className="mt-2 rounded-md border border-inzbc-navy/20 bg-inzbc-navy/5 p-2 text-xs font-medium text-inzbc-navy">
          {GOVERNANCE_LINE}
        </p>
      </div>

      {report.state === 'QA Failed' ? (
        <p role="status" className="rounded-md border border-inzbc-crimson bg-inzbc-crimson/10 p-3 text-sm text-inzbc-crimson">
          This run failed QA and has been returned for correction. Showing the last-reviewed
          content below.
        </p>
      ) : null}

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-inzbc-navy">Digest content for review</h3>
        {report.sections.map((section) => (
          <div key={section.id} className={`rounded-md border p-3 ${SECTION_CARD_CLASSES[section.reviewStatus]}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="text-sm font-medium text-inzbc-navy">{section.title}</h4>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  aria-pressed={section.reviewStatus === 'approved'}
                  onClick={() => setSectionReviewStatus(section.id, 'approved')}
                  className={`rounded-md border px-2 py-1 text-xs font-medium ${
                    section.reviewStatus === 'approved'
                      ? 'border-inzbc-forest bg-inzbc-forest text-white'
                      : 'border-inzbc-navy/20 text-inzbc-navy'
                  }`}
                >
                  Approve
                </button>
                <button
                  type="button"
                  aria-pressed={section.reviewStatus === 'flagged'}
                  onClick={() => setSectionReviewStatus(section.id, 'flagged')}
                  className={`rounded-md border px-2 py-1 text-xs font-medium ${
                    section.reviewStatus === 'flagged'
                      ? 'border-inzbc-crimson bg-inzbc-crimson text-white'
                      : 'border-inzbc-navy/20 text-inzbc-navy'
                  }`}
                >
                  Flag
                </button>
                {/* min-h-11 (44px): unlike the padded Approve/Flag buttons beside it, this was a
                    bare underlined text link with no padding — its hit area was just the glyph
                    width of "Edit"/"Done" at text-xs, well under a usable mobile touch target. */}
                <button
                  type="button"
                  onClick={() => setEditingId(editingId === section.id ? null : section.id)}
                  className="min-h-11 px-2 text-xs font-medium text-inzbc-blue underline"
                >
                  {editingId === section.id ? 'Done' : 'Edit'}
                </button>
              </div>
            </div>
            {editingId === section.id ? (
              <>
                <label htmlFor={`${editFieldId}-${section.id}`} className="sr-only">
                  Edit content for {section.title}
                </label>
                <textarea
                  id={`${editFieldId}-${section.id}`}
                  className="mt-1 min-h-20 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm text-slate-700 transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                  value={section.content}
                  onChange={(event) => updateSectionContent(section.id, event.target.value)}
                />
              </>
            ) : (
              <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                {section.content || <span className="italic text-slate-600">No content recorded.</span>}
              </p>
            )}
            {section.reviewStatus === 'flagged' ? (
              <div className="mt-2">
                <label htmlFor={`${editFieldId}-reason-${section.id}`} className="text-xs font-medium text-inzbc-crimson">
                  Reason for flagging
                </label>
                <input
                  id={`${editFieldId}-reason-${section.id}`}
                  type="text"
                  className="mt-1 w-full rounded-md border border-inzbc-crimson/50 p-2 text-sm text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-crimson"
                  value={section.flagReason}
                  placeholder="What needs correction before this can be approved?"
                  onChange={(event) => setSectionFlagReason(section.id, event.target.value)}
                />
              </div>
            ) : null}
          </div>
        ))}
      </div>

      {/* Section breakdown is a rollup of the approve/flag choices above — presentational, not a
          second scoring model. The checklist score below is the one grounded in an actual
          completed check (SIP-188), which is why it's labelled separately rather than merged into
          one invented "quality score." */}
      <div className="rounded-md border border-inzbc-navy/10 bg-white shadow-sm p-3">
        <h3 className="text-sm font-semibold text-inzbc-navy">Section review breakdown</h3>
        <dl className="mt-2 grid grid-cols-3 gap-2 text-center text-sm">
          <div>
            <dt className="text-xs text-slate-500">Approved</dt>
            <dd className="text-lg font-semibold text-inzbc-forest">{sectionBreakdown.approved}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Flagged</dt>
            <dd className="text-lg font-semibold text-inzbc-crimson">{sectionBreakdown.flagged}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Pending</dt>
            <dd className="text-lg font-semibold text-slate-500">{sectionBreakdown.pending}</dd>
          </div>
        </dl>
        <p className="mt-2 text-xs text-slate-500">
          of {sectionBreakdown.total} digest sections. Checklist pass rate:{' '}
          <strong className="text-inzbc-navy">{checklistScore}%</strong> ({passCount}/{answeredCount} answered
          {criticalFailCount > 0 ? (
            <span className="text-inzbc-crimson"> · {criticalFailCount} Critical failure(s)</span>
          ) : null}
          ).
        </p>
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-inzbc-navy">3. Critical and High signals</h3>
        {report.criticalHighSignals.length === 0 ? (
          <p className="text-sm text-slate-500">No Critical/High signals recorded for this run.</p>
        ) : (
          report.criticalHighSignals.map((signal) => (
            <div key={signal.id} className="rounded-md border border-inzbc-navy/10 bg-white shadow-sm p-3">
              {/* flex-wrap: missing here, unlike every other card header in this screen — a long
                  headline next to the strength badge would force this row wider than its
                  container at narrow viewports (WCAG 2.2 §1.4.10) instead of just wrapping. */}
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h4 className="text-sm font-medium text-inzbc-navy">{signal.headline}</h4>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                  {signal.signalStrength}
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-700">{signal.whatHappened}</p>
              <p className="mt-1 text-xs text-slate-500">
                Verification: {signal.verificationStatus} · Source confidence: {signal.sourceConfidence}
              </p>
            </div>
          ))
        )}
      </div>

      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-inzbc-navy">SIP-188 QA checklist</h3>
        {report.qaChecklist.map((group) => (
          <div key={group.id} className="rounded-md border border-inzbc-navy/10 bg-white shadow-sm p-3">
            <h4 className="text-sm font-medium text-inzbc-navy">{group.title}</h4>
            <ul className="mt-2 space-y-2">
              {group.items.map((item) => (
                <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-2 first:border-t-0 first:pt-0">
                  <span className="text-sm text-slate-700">
                    {item.text}
                    {item.critical ? (
                      <span className="ml-1 rounded-full bg-inzbc-crimson/10 px-1.5 py-0.5 text-xs font-semibold text-inzbc-crimson">
                        Critical
                      </span>
                    ) : null}
                  </span>
                  <span role="group" aria-label={item.text} className="flex gap-1">
                    {/* Critical items don't offer N/A: none of SIP-188's five Critical checks
                        (a2, b2, c3, d4, e1) describe something that can legitimately not apply to
                        a run, and reportsStore.submitQaResult treats Critical+N/A as a failure
                        anyway — better to not offer a choice the store rejects. */}
                    {QA_ANSWERS.filter((option) => !item.critical || option.value !== 'na').map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        aria-pressed={item.answer === option.value}
                        onClick={() => setChecklistAnswer(group.id, item.id, option.value)}
                        className={`rounded-md border px-2 py-1 text-xs font-medium ${
                          item.answer === option.value
                            ? option.value === 'fail'
                              ? 'border-inzbc-crimson bg-inzbc-crimson text-white'
                              : 'border-inzbc-forest bg-inzbc-forest text-white'
                            : 'border-inzbc-navy/20 text-inzbc-navy'
                        }`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* docs/sip-ui-spec.md Screen 2: "Any Critical failure disables 'Submit to CEO' entirely
          ... The only path forward from a Critical fail is 'Send back for correction.'" This must
          *visibly* block, not just silently produce a different outcome after the same-looking
          button is clicked — so as soon as any Critical item reads Fail, the primary action
          switches to the crimson, correction-labelled button before submission, not only after
          (reportsStore.submitQaResult still computes pass/fail from the checklist and enforces
          this server-side too; this is the client-side half of "fail closed"). */}
      {report.state !== 'QA Failed' ? (
        <div>
          <label htmlFor={notesFieldId} className="text-sm font-semibold text-inzbc-navy">
            QA notes
          </label>
          <textarea
            id={notesFieldId}
            className="mt-1 min-h-16 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm text-slate-700 transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
            value={notes}
            placeholder="What was checked, and why this result — required to record a QA result."
            onChange={(event) => setNotes(event.target.value)}
          />
        </div>
      ) : null}

      <div className="space-y-2">
        {report.state === 'QA Failed' ? (
          <button
            type="button"
            onClick={() => void onSendBackForCorrection()}
            disabled={submitState.kind === 'loading'}
            className="rounded-md bg-inzbc-crimson px-4 py-2 font-semibold text-white disabled:cursor-progress disabled:opacity-60"
          >
            {submitState.kind === 'loading' ? 'Sending back…' : 'Send back for correction'}
          </button>
        ) : criticalFailCount > 0 ? (
          <button
            type="button"
            onClick={() => void onRecordResult()}
            disabled={!allAnswered || !notes.trim() || submitState.kind === 'loading'}
            className="rounded-md bg-inzbc-crimson px-4 py-2 font-semibold text-white disabled:cursor-progress disabled:opacity-60"
          >
            {submitState.kind === 'loading'
              ? 'Recording…'
              : 'Record Critical fail — sends this run back for correction'}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => void onRecordResult()}
            disabled={!allAnswered || !notes.trim() || submitState.kind === 'loading'}
            className="rounded-md bg-inzbc-tangerine px-4 py-2 font-semibold text-inzbc-navy transition-colors hover:enabled:bg-inzbc-tangerine/90 disabled:cursor-progress disabled:opacity-60"
          >
            {submitState.kind === 'loading' ? 'Recording…' : 'Record QA result'}
          </button>
        )}
        {!allAnswered && report.state !== 'QA Failed' ? (
          <p className="text-xs text-slate-500">
            {checklistItems.length - answeredCount} checklist item(s) still need Pass/Fail/N/A before a result
            can be recorded.
          </p>
        ) : null}
        {allAnswered && !notes.trim() && report.state !== 'QA Failed' ? (
          <p className="text-xs text-slate-500">QA notes are required before a result can be recorded.</p>
        ) : null}
        {submitState.kind === 'error' ? (
          <p role="alert" className="text-sm text-inzbc-crimson">
            {submitState.message}
          </p>
        ) : null}
        {report.qa ? (
          <p role="status" className="text-sm text-slate-600">
            Last recorded result: <strong>{report.qa.result}</strong> — {report.qa.reviewer},{' '}
            {report.qa.timestamp}
            {report.qa.criticalFailuresFound ? ` · Critical: ${report.qa.criticalFailuresFound}` : ''}
          </p>
        ) : null}
      </div>
    </section>
  )
}
