import { useCallback, useEffect, useRef, useState } from 'react'
import { DashboardApiError, type DashboardOut, getDashboard } from '../api/dashboardClient'
import { stateBadgeClass } from '../lib/runState'

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'loaded'; dashboard: DashboardOut }

const GATE_LABELS: Record<keyof DashboardOut['gates'], string> = {
  qa_status: 'QA status',
  report_approval: 'Report approval',
  distribution_authority: 'Distribution authority',
  distribution_recipient: 'Distribution recipient',
}

/**
 * The executive view (docs/modules/dashboards.md): current run + control state, candidate
 * coverage, QA/distribution gates, open actions — all from the one `/api/dashboard` read (#47),
 * replacing the earlier client-side composition of `listRuns()[0]` + `listCandidates()`.
 */
export function ExecutiveOverview() {
  const [state, setState] = useState<LoadState>({ kind: 'loading' })
  // One request in flight at a time: Refresh aborts the previous one, so a slower older response
  // can never overwrite a newer one, and unmounting aborts whatever is still pending.
  const inFlight = useRef<AbortController | null>(null)

  const fetchDashboard = useCallback(() => {
    inFlight.current?.abort()
    const controller = new AbortController()
    inFlight.current = controller
    getDashboard({ signal: controller.signal })
      .then((dashboard) => {
        if (!controller.signal.aborted) setState({ kind: 'loaded', dashboard })
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setState({
          kind: 'error',
          message: error instanceof DashboardApiError ? error.message : 'Something went wrong. Please try again.',
        })
      })
  }, [])

  useEffect(() => {
    fetchDashboard()
    return () => inFlight.current?.abort()
  }, [fetchDashboard])

  function reload() {
    setState({ kind: 'loading' })
    fetchDashboard()
  }

  return (
    <section className="space-y-4" aria-labelledby="executive-overview-heading">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="executive-overview-heading" className="text-lg font-semibold text-inzbc-navy">
          Executive view
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
          Loading dashboard…
        </p>
      ) : null}

      {state.kind === 'error' ? (
        <p role="alert" className="rounded-md border border-inzbc-crimson bg-inzbc-crimson/10 p-3 text-sm text-inzbc-crimson">
          {state.message}
        </p>
      ) : null}

      {state.kind === 'loaded' ? (
        <div className="space-y-4">
          <div className="rounded-md border border-inzbc-navy/10 bg-white p-4 shadow-sm">
            {state.dashboard.run === null ? (
              <p className="text-sm text-slate-600">No SIP runs recorded yet.</p>
            ) : (
              <>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-inzbc-navy">{state.dashboard.run.run_number}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Coverage {state.dashboard.run.coverage_start_utc} – {state.dashboard.run.coverage_end_utc}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      Prompt {state.dashboard.run.prompt_version} · v{state.dashboard.run.version}
                    </p>
                  </div>
                  <span
                    className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${stateBadgeClass(state.dashboard.run.state)}`}
                  >
                    {state.dashboard.run.state}
                  </span>
                </div>

                <div className="mt-4 border-t border-inzbc-navy/10 pt-4">
                  <h3 className="text-sm font-medium text-inzbc-navy">Candidate coverage</h3>
                  {state.dashboard.coverage.total === 0 ? (
                    <p className="mt-1 text-sm text-slate-600">No candidates captured for this run yet.</p>
                  ) : (
                    <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
                      <div>
                        <dt className="text-slate-500">Total captured</dt>
                        <dd className="font-medium text-inzbc-navy">{state.dashboard.coverage.total}</dd>
                      </div>
                      <div>
                        <dt className="text-slate-500">Included</dt>
                        <dd className="font-medium text-inzbc-navy">{state.dashboard.coverage.included}</dd>
                      </div>
                      {Object.entries(state.dashboard.coverage.by_verification).map(([verification, count]) => (
                        <div key={verification}>
                          <dt className="text-slate-500">{verification}</dt>
                          <dd className="font-medium text-inzbc-navy">{count}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                </div>

                <div className="mt-4 border-t border-inzbc-navy/10 pt-4">
                  <h3 className="text-sm font-medium text-inzbc-navy">QA &amp; distribution</h3>
                  <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
                    {(Object.keys(GATE_LABELS) as Array<keyof DashboardOut['gates']>).map((key) => (
                      <div key={key}>
                        <dt className="text-slate-500">{GATE_LABELS[key]}</dt>
                        <dd className="font-medium text-inzbc-navy">{state.dashboard.gates[key] ?? '—'}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </>
            )}
          </div>

          <div className="rounded-md border border-inzbc-navy/10 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-medium text-inzbc-navy">Open actions</h3>
            {state.dashboard.open_actions.length === 0 ? (
              <p className="mt-2 text-sm text-slate-600">No open actions.</p>
            ) : (
              <ul className="mt-2 divide-y divide-inzbc-navy/10">
                {state.dashboard.open_actions.map((action) => (
                  <li key={action.action_code} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                    <div>
                      <p className="font-medium text-inzbc-navy">{action.title}</p>
                      <p className="text-xs text-slate-500">
                        {action.action_code}
                        {action.owner ? ` · ${action.owner}` : ''}
                        {action.due_date ? ` · due ${action.due_date}` : ''}
                      </p>
                    </div>
                    <span
                      className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${
                        action.overdue ? 'bg-inzbc-crimson/10 text-inzbc-crimson' : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {action.overdue ? 'Overdue' : action.status}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {state.dashboard.open_actions_truncated ? (
              <p className="mt-2 text-xs text-slate-500">More open actions exist than are shown here.</p>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  )
}
