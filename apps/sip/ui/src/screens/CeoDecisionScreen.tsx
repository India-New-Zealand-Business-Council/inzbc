import { useState } from 'react'
import { GOVERNANCE_LINE, type DailyBriefReport, type ReportDecisionType } from '../domain'

interface Props {
  report: DailyBriefReport
  onChange: (report: DailyBriefReport) => void
}

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
 * combined control." This commit builds the read-only digest preview and the report-decision
 * *choice* (which of Continue / Continue With Correction / Pause / Stop). The required
 * reason/conditions/owner/evidence/next-review-date fields and the actual submit action land in a
 * later commit; the separate distribution-authorisation action lands after that — deliberately
 * split so the two decisions can never be wired as one submit by construction.
 */
export function CeoDecisionScreen({ report }: Props) {
  const [selectedDecision, setSelectedDecision] = useState<ReportDecisionType | null>(null)

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
      ) : (
        <p role="status" className="text-sm text-slate-600">
          Report decision already recorded: <strong>{report.decision?.decision ?? report.state}</strong>.
        </p>
      )}
    </section>
  )
}
