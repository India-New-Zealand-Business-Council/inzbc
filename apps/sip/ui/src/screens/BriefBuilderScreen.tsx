import { useId, useMemo, useRef, useState } from 'react'
import { ReportsApiError, submitReportForQa } from '../api/reportsStore'
import type { Candidate, DailyBriefReport, SourceOutcome } from '../domain'
import { candidatesFixture } from '../lib/fixtures'
import { FOCUS_NOTE_MAX_LENGTH, validateBrief } from '../lib/validation'

type SubmitState = { kind: 'idle' } | { kind: 'loading' } | { kind: 'error'; message: string }

const OUTCOME_OPTIONS: SourceOutcome[] = [
  '',
  'Included',
  'Context',
  'Suppressed',
  'Inaccessible',
  'Excluded',
  'No Qualifying Item',
]

interface Props {
  report: DailyBriefReport
  onChange: (report: DailyBriefReport) => void
}

/**
 * docs/sip-ui-spec.md Screen 1: "The builder assembles the SIP-186 brief from [scored candidate]
 * data — it is not a blank free-text form." Fields below map onto the SIP-186 run header:
 * - date range picker -> the coverage window (start/end, Pacific/Auckland).
 * - source selection -> the scored candidates (GET /api/candidates?run=:id fixture below) that
 *   feed today's brief, not a source-library toggle — SIP-186 §12's mandatory-source table is a
 *   separate, fixed checklist, not something the analyst selects from.
 * - "digest topic" (the task's own wording) has no equivalent named field in SIP-186. Modelled
 *   here as an optional working note (`focusNote`), explicitly labelled as non-canonical, rather
 *   than silently inventing a "topic" field the source template doesn't have.
 * Run ID / analyst / reviewer are read-only: docs/sip-ui-spec.md is explicit that reviewer
 * identity "comes from the authenticated session, not a free field" — there is no live auth yet
 * (docs/api-integration-spec.md), so these render as fixed run-header data, not editable inputs.
 */
export function BriefBuilderScreen({ report, onChange }: Props) {
  const [candidates] = useState<Candidate[]>(() => candidatesFixture())
  const [selectedCandidateIds, setSelectedCandidateIds] = useState<Set<string>>(new Set())
  const [submitState, setSubmitState] = useState<SubmitState>({ kind: 'idle' })
  const inFlight = useRef<AbortController | null>(null)
  const reportDateId = useId()
  const coverageStartId = useId()
  const coverageEndId = useId()
  const focusNoteId = useId()

  const errors = useMemo(
    () => validateBrief(report, selectedCandidateIds.size),
    [report, selectedCandidateIds],
  )
  const isDraft = report.state === 'Report Drafted'

  async function onSubmitForQa() {
    if (errors.length > 0 || !isDraft) return
    inFlight.current?.abort()
    const controller = new AbortController()
    inFlight.current = controller
    setSubmitState({ kind: 'loading' })

    try {
      const updated = await submitReportForQa(report, selectedCandidateIds.size, { signal: controller.signal })
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

  function toggleCandidate(id: string) {
    setSelectedCandidateIds((previous) => {
      const next = new Set(previous)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function setSourceOutcome(sourceId: string, outcome: SourceOutcome) {
    onChange({
      ...report,
      sourceCoverage: report.sourceCoverage.map((row) =>
        row.sourceId === sourceId ? { ...row, outcome } : row,
      ),
    })
  }

  function setSourceFallback(sourceId: string, fallbackAttempt: string) {
    onChange({
      ...report,
      sourceCoverage: report.sourceCoverage.map((row) =>
        row.sourceId === sourceId ? { ...row, fallbackAttempt } : row,
      ),
    })
  }

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-inzbc-navy">Brief Builder</h2>
        <p className="mt-1 text-sm text-slate-600">
          Assemble the SIP-186 daily brief from scored candidates (Analyst).
        </p>
      </div>

      {!isDraft ? (
        <p role="status" className="rounded-md border border-inzbc-forest bg-inzbc-forest/10 p-3 text-sm text-inzbc-forest">
          Submitted for QA — this run is now <strong>{report.state}</strong>. Further edits happen
          on the QA Review screen, not here.
        </p>
      ) : null}

      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-md border border-slate-200 bg-white p-4 text-sm sm:grid-cols-4">
        <div>
          <dt className="font-semibold text-inzbc-navy">Run ID</dt>
          <dd className="text-slate-700">{report.runId}</dd>
        </div>
        <div>
          <dt className="font-semibold text-inzbc-navy">Analyst</dt>
          <dd className="text-slate-700">{report.analyst}</dd>
        </div>
        <div>
          <dt className="font-semibold text-inzbc-navy">Reviewer</dt>
          <dd className="text-slate-700">{report.reviewer}</dd>
        </div>
        <div>
          <dt className="font-semibold text-inzbc-navy">Approved version set</dt>
          <dd className="text-slate-700">{report.approvedVersionSet}</dd>
        </div>
      </dl>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <label htmlFor={reportDateId} className="mb-1 block text-sm font-semibold text-inzbc-navy">
            Report / brief date
          </label>
          <input
            id={reportDateId}
            type="date"
            value={report.reportDate}
            onChange={(event) => onChange({ ...report, reportDate: event.target.value })}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label htmlFor={coverageStartId} className="mb-1 block text-sm font-semibold text-inzbc-navy">
            Coverage window start (Pacific/Auckland)
          </label>
          <input
            id={coverageStartId}
            type="date"
            value={report.coverageStart}
            onChange={(event) => onChange({ ...report, coverageStart: event.target.value })}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label htmlFor={coverageEndId} className="mb-1 block text-sm font-semibold text-inzbc-navy">
            Coverage window end (Pacific/Auckland)
          </label>
          <input
            id={coverageEndId}
            type="date"
            value={report.coverageEnd}
            onChange={(event) => onChange({ ...report, coverageEnd: event.target.value })}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div>
        <div className="mb-1 flex items-baseline justify-between gap-3">
          <label htmlFor={focusNoteId} className="block text-sm font-semibold text-inzbc-navy">
            Focus note <span className="font-normal text-slate-500">(optional — not a SIP-186 field)</span>
          </label>
          <span
            className={`text-xs ${
              report.focusNote.length > FOCUS_NOTE_MAX_LENGTH ? 'font-semibold text-inzbc-crimson' : 'text-slate-500'
            }`}
          >
            {report.focusNote.length} / {FOCUS_NOTE_MAX_LENGTH}
          </span>
        </div>
        <input
          id={focusNoteId}
          type="text"
          value={report.focusNote}
          onChange={(event) => onChange({ ...report, focusNote: event.target.value })}
          placeholder="A short working note for this run, e.g. a theme to watch for"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold text-inzbc-navy">
          12. Source coverage and exceptions — mandatory sources
        </h3>
        <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
          <table className="w-full min-w-[36rem] text-left text-sm">
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
              <tr>
                <th scope="col" className="px-3 py-2">
                  Source
                </th>
                <th scope="col" className="px-3 py-2">
                  Outcome
                </th>
                <th scope="col" className="px-3 py-2">
                  Fallback attempt (if inaccessible/excluded)
                </th>
              </tr>
            </thead>
            <tbody>
              {report.sourceCoverage.map((row) => {
                return (
                  <tr key={row.sourceId} className="border-b border-slate-100 last:border-0">
                    <td className="px-3 py-2 align-top">
                      <span className="block font-medium text-inzbc-navy">{row.sourceName}</span>
                      <span className="block text-xs text-slate-500">{row.sip185Code}</span>
                    </td>
                    <td className="px-3 py-2 align-top">
                      <label className="sr-only" htmlFor={`outcome-${row.sourceId}`}>
                        Outcome for {row.sourceName}
                      </label>
                      <select
                        id={`outcome-${row.sourceId}`}
                        value={row.outcome}
                        onChange={(event) => setSourceOutcome(row.sourceId, event.target.value as SourceOutcome)}
                        className={`rounded-md border px-2 py-1 text-sm ${
                          row.mandatory && row.outcome === '' ? 'border-inzbc-crimson' : 'border-slate-300'
                        }`}
                      >
                        {OUTCOME_OPTIONS.map((option) => (
                          <option key={option || 'blank'} value={option}>
                            {option || '— not recorded —'}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2 align-top">
                      <label className="sr-only" htmlFor={`fallback-${row.sourceId}`}>
                        Fallback attempt for {row.sourceName}
                      </label>
                      <input
                        id={`fallback-${row.sourceId}`}
                        type="text"
                        value={row.fallbackAttempt}
                        onChange={(event) => setSourceFallback(row.sourceId, event.target.value)}
                        className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                      />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {isDraft && errors.length > 0 ? (
        <div role="alert" className="rounded-md border border-inzbc-crimson bg-inzbc-crimson/10 p-3 text-sm text-inzbc-crimson">
          <p className="font-semibold">Before this brief can be submitted for QA:</p>
          <ul className="mt-1 list-inside list-disc">
            {errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {isDraft && errors.length === 0 ? (
        <p className="text-sm font-medium text-inzbc-forest">Ready to submit for QA.</p>
      ) : null}

      {isDraft ? (
        <div>
          <button
            type="button"
            onClick={() => void onSubmitForQa()}
            disabled={errors.length > 0 || submitState.kind === 'loading'}
            className="rounded-md bg-inzbc-tangerine px-4 py-2 font-semibold text-white disabled:cursor-progress disabled:opacity-60"
          >
            {submitState.kind === 'loading' ? 'Submitting…' : 'Submit for QA'}
          </button>
          {submitState.kind === 'error' ? (
            <p role="alert" className="mt-2 text-sm text-inzbc-crimson">
              {submitState.message}
            </p>
          ) : null}
        </div>
      ) : null}

      <div>
        <h3 className="mb-2 text-sm font-semibold text-inzbc-navy">
          Source selection — scored candidates for this run
        </h3>
        <ul className="space-y-2">
          {candidates.map((candidate) => (
            <li key={candidate.id} className="rounded-md border border-slate-200 bg-white p-3">
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={selectedCandidateIds.has(candidate.id)}
                  onChange={() => toggleCandidate(candidate.id)}
                  className="mt-1"
                />
                <span>
                  <span className="block text-sm font-medium text-inzbc-navy">{candidate.headline}</span>
                  <span className="mt-0.5 block text-xs text-slate-500">
                    {candidate.sourceName} · {candidate.sector} · {candidate.signalStrength} signal ·{' '}
                    {candidate.verificationStatus}
                  </span>
                </span>
              </label>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-slate-500">{selectedCandidateIds.size} candidate(s) selected</p>
      </div>
    </section>
  )
}
