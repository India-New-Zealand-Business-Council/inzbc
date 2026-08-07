import { useCallback, useEffect, useState } from 'react'
import { listRuns, type RunOut, SipApiError } from '../api/runsClient'

interface Props {
  onSelectRun: (runId: string) => void
}

type LoadState = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'loaded'; runs: RunOut[] }

// Navy background = neutral/unstarted, matching the "pending" treatment elsewhere in this app
// (QaReviewScreen's SECTION_CARD_CLASSES); forest = a healthy in-progress/closed state; tangerine
// = needs attention (paused, awaiting a decision); crimson = stopped. Not exhaustive of all 18
// RunState values (schemas/state-machine.md) — states this screen's four actions never produce
// (Scanning, Report Drafted, etc.) fall back to the neutral badge rather than getting a bespoke
// colour for a state this UI cannot reach.
const STATE_BADGE_CLASSES: Record<string, string> = {
  Draft: 'bg-slate-100 text-slate-700',
  'Run Authorised': 'bg-inzbc-forest/10 text-inzbc-forest',
  'Coverage Locked': 'bg-inzbc-forest/10 text-inzbc-forest',
  'Awaiting CEO Decision': 'bg-inzbc-tangerine/20 text-inzbc-navy',
  Paused: 'bg-inzbc-tangerine/20 text-inzbc-navy',
  Stopped: 'bg-inzbc-crimson/10 text-inzbc-crimson',
  Distributed: 'bg-inzbc-forest/10 text-inzbc-forest',
  Closed: 'bg-slate-200 text-slate-700',
}

export function stateBadgeClass(state: string): string {
  return STATE_BADGE_CLASSES[state] ?? 'bg-slate-100 text-slate-700'
}

/**
 * Runs list (#237). Fetches on mount and exposes `reload` so a caller that just changed a run's
 * state (e.g. via a lifecycle action) can refresh this list rather than it going stale — added in
 * a later commit alongside the action buttons themselves.
 */
export function RunsListScreen({ onSelectRun }: Props) {
  const [state, setState] = useState<LoadState>({ kind: 'loading' })

  const load = useCallback((signal?: AbortSignal) => {
    setState({ kind: 'loading' })
    listRuns({ signal })
      .then((runs) => setState({ kind: 'loaded', runs }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setState({
          kind: 'error',
          message: error instanceof SipApiError ? error.message : 'Something went wrong. Please try again.',
        })
      })
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal)
    return () => controller.abort()
  }, [load])

  return (
    <section className="space-y-4" aria-labelledby="runs-list-heading">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 id="runs-list-heading" className="text-lg font-semibold text-inzbc-navy">
            Runs
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Every SIP run recorded in the database (`/api/runs`, #237). Select a run to see its
            candidates and lifecycle actions.
          </p>
        </div>
        <button
          type="button"
          onClick={() => load()}
          className="min-h-11 rounded-md border border-inzbc-navy/20 px-3 py-2 text-sm font-medium text-inzbc-navy transition-colors hover:border-inzbc-navy/40"
        >
          Refresh
        </button>
      </div>

      {state.kind === 'loading' ? (
        <p role="status" className="text-sm text-slate-600">
          Loading runs…
        </p>
      ) : null}

      {state.kind === 'error' ? (
        <p role="alert" className="rounded-md border border-inzbc-crimson bg-inzbc-crimson/10 p-3 text-sm text-inzbc-crimson">
          {state.message}
        </p>
      ) : null}

      {state.kind === 'loaded' && state.runs.length === 0 ? (
        <p className="text-sm text-slate-600">No runs recorded yet.</p>
      ) : null}

      {state.kind === 'loaded' && state.runs.length > 0 ? (
        <ul className="space-y-2">
          {state.runs.map((run) => (
            <li key={run.id} className="rounded-md border border-inzbc-navy/10 bg-white shadow-sm p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-inzbc-navy">{run.run_number}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Coverage {run.coverage_start_utc} – {run.coverage_end_utc}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Prompt {run.prompt_version} · v{run.version}
                  </p>
                </div>
                <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${stateBadgeClass(run.state)}`}>
                  {run.state}
                </span>
              </div>
              <button
                type="button"
                onClick={() => onSelectRun(run.id)}
                className="mt-2 min-h-11 rounded-md border border-inzbc-navy/20 px-3 py-2 text-sm font-medium text-inzbc-navy transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
              >
                View run and candidates
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
