import { useId, useState } from 'react'
import type { DailyBriefReport } from '../domain'

interface Props {
  report: DailyBriefReport
  onChange: (report: DailyBriefReport) => void
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
          <div key={section.id} className="rounded-md border border-slate-200 bg-white p-3">
            <div className="flex items-center justify-between gap-2">
              <h4 className="text-sm font-medium text-inzbc-navy">{section.title}</h4>
              <button
                type="button"
                onClick={() => setEditingId(editingId === section.id ? null : section.id)}
                className="text-xs font-medium text-inzbc-blue underline"
              >
                {editingId === section.id ? 'Done' : 'Edit'}
              </button>
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
