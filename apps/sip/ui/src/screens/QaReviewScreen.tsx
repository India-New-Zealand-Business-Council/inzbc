import { useId, useState } from 'react'
import type { DailyBriefReport, ReviewStatus } from '../domain'

interface Props {
  report: DailyBriefReport
  onChange: (report: DailyBriefReport) => void
}

// Colour-coded per the brand palette rather than arbitrary colours: forest = approved (same
// "healthy" association as the rest of this UI), crimson = flagged (matches the alert/error
// colour used everywhere else in this component), slate = still pending, nothing decided yet.
const SECTION_CARD_CLASSES: Record<ReviewStatus, string> = {
  pending: 'border-slate-200 bg-white',
  approved: 'border-inzbc-forest bg-inzbc-forest/5',
  flagged: 'border-inzbc-crimson bg-inzbc-crimson/5',
}

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
  const editFieldId = useId()

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

  if (report.reviewer && report.reviewer === report.analyst) {
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
                      : 'border-slate-300 text-inzbc-navy'
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
                      : 'border-slate-300 text-inzbc-navy'
                  }`}
                >
                  Flag
                </button>
                <button
                  type="button"
                  onClick={() => setEditingId(editingId === section.id ? null : section.id)}
                  className="text-xs font-medium text-inzbc-blue underline"
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
                  className="mt-1 min-h-20 w-full rounded-md border border-slate-300 p-2 text-sm text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                  value={section.content}
                  onChange={(event) => updateSectionContent(section.id, event.target.value)}
                />
              </>
            ) : (
              <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                {section.content || <span className="italic text-slate-400">No content recorded.</span>}
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

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-inzbc-navy">3. Critical and High signals</h3>
        {report.criticalHighSignals.length === 0 ? (
          <p className="text-sm text-slate-500">No Critical/High signals recorded for this run.</p>
        ) : (
          report.criticalHighSignals.map((signal) => (
            <div key={signal.id} className="rounded-md border border-slate-200 bg-white p-3">
              <div className="flex items-center justify-between gap-2">
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
    </section>
  )
}
