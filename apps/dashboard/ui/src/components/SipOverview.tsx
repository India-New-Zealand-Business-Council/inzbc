import { useCallback, useEffect, useState } from 'react'
import { type CandidateOut, listCandidates } from '../api/candidatesClient'
import { DashboardApiError } from '../api/httpClient'
import { listRuns, type RunOut } from '../api/runsClient'
import { summarizeCandidates, VERIFICATION_STATES } from '../lib/candidateSummary'
import { stateBadgeClass } from '../lib/runState'

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'no-runs' }
  | { kind: 'loaded'; run: RunOut; candidates: CandidateOut[] }

/**
 * "Current SIP run status" + "Source/candidate coverage summary" (docs/modules/dashboards.md's
 * Executive view). The current run is `listRuns()[0]` — `services/api/persistence.py:list_runs`
 * orders most-recently-created first — then that run's candidates are fetched for the coverage
 * counts. Split from the effect body (react-hooks/set-state-in-effect), same pattern as
 * apps/sip/ui's RunsListScreen.
 */
export function SipOverview() {
  const [state, setState] = useState<LoadState>({ kind: 'loading' })

  const fetchOverview = useCallback((signal?: AbortSignal) => {
    listRuns({ signal })
      .then((runs) => {
        const run = runs[0]
        if (!run) {
          setState({ kind: 'no-runs' })
          return
        }
        return listCandidates(run.id, { signal }).then((candidates) => {
          setState({ kind: 'loaded', run, candidates })
        })
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setState({
          kind: 'error',
          message: error instanceof DashboardApiError ? error.message : 'Something went wrong. Please try again.',
        })
      })
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    fetchOverview(controller.signal)
    return () => controller.abort()
  }, [fetchOverview])

  function reload() {
    setState({ kind: 'loading' })
    fetchOverview()
  }

  return (
    <section className="space-y-4" aria-labelledby="sip-overview-heading">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="sip-overview-heading" className="text-lg font-semibold text-inzbc-navy">
          SIP: Current run
        </h2>
        <button
          type="button"
          onClick={reload}
          className="min-h-11 rounded-md border border-inzbc-navy/20 px-3 py-2 text-sm font-medium text-inzbc-navy transition-colors hover:border-inzbc-navy/40"
        >
          Refresh
        </button>
      </div>

      {state.kind === 'loading' ? (
        <p role="status" className="text-sm text-slate-600">
          Loading current run…
        </p>
      ) : null}

      {state.kind === 'error' ? (
        <p role="alert" className="rounded-md border border-inzbc-crimson bg-inzbc-crimson/10 p-3 text-sm text-inzbc-crimson">
          {state.message}
        </p>
      ) : null}

      {state.kind === 'no-runs' ? (
        <p className="text-sm text-slate-600">No SIP runs recorded yet.</p>
      ) : null}

      {state.kind === 'loaded' ? (
        <div className="rounded-md border border-inzbc-navy/10 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-sm font-medium text-inzbc-navy">{state.run.run_number}</p>
              <p className="mt-1 text-xs text-slate-500">
                Coverage {state.run.coverage_start_utc} – {state.run.coverage_end_utc}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Prompt {state.run.prompt_version} · v{state.run.version}
              </p>
            </div>
            <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${stateBadgeClass(state.run.state)}`}>
              {state.run.state}
            </span>
          </div>

          <div className="mt-4 border-t border-inzbc-navy/10 pt-4">
            <h3 className="text-sm font-medium text-inzbc-navy">Candidate coverage</h3>
            {state.candidates.length === 0 ? (
              <p className="mt-1 text-sm text-slate-600">No candidates captured for this run yet.</p>
            ) : (
              (() => {
                const summary = summarizeCandidates(state.candidates)
                return (
                  <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
                    <div>
                      <dt className="text-slate-500">Total captured</dt>
                      <dd className="font-medium text-inzbc-navy">{summary.total}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">Included</dt>
                      <dd className="font-medium text-inzbc-navy">{summary.included}</dd>
                    </div>
                    {VERIFICATION_STATES.map((verification) => (
                      <div key={verification}>
                        <dt className="text-slate-500">{verification}</dt>
                        <dd className="font-medium text-inzbc-navy">{summary.byVerification[verification]}</dd>
                      </div>
                    ))}
                  </dl>
                )
              })()
            )}
          </div>
        </div>
      ) : null}
    </section>
  )
}
