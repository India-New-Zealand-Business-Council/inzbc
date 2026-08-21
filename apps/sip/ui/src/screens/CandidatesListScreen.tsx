import { useCallback, useEffect, useState } from 'react'
import { listCandidates, type CandidateOut, SipApiError } from '../api/candidatesClient'
import { CandidateActionPanel } from '../components/CandidateActionPanel'
import { signalBadgeClass, verificationBadgeClass } from '../lib/candidateState'

interface Props {
  runId: string
  onSelectCandidate: (candidateId: string) => void
}

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'loaded'; candidates: CandidateOut[] }

/**
 * Candidates captured for one run (`GET /api/candidates?run=:id`, #242) plus the four candidate
 * commands (verify/score/route/merge, `CandidateActionPanel`) — always scoped to a run, since the
 * endpoint requires the `run` query param; there is no global candidates list. Rendered inside
 * RunDetailScreen rather than reachable on its own, but kept as its own component/file so it's
 * independently reusable and testable.
 */
export function CandidatesListScreen({ runId, onSelectCandidate }: Props) {
  const [state, setState] = useState<LoadState>({ kind: 'loading' })

  /** Replaces one candidate in place after a successful action, rather than re-fetching the whole
   * list — the action's own response is already the authoritative updated record. */
  function updateCandidate(updated: CandidateOut) {
    setState((current) =>
      current.kind === 'loaded'
        ? { kind: 'loaded', candidates: current.candidates.map((c) => (c.id === updated.id ? updated : c)) }
        : current,
    )
  }

  const fetchCandidates = useCallback(
    (signal?: AbortSignal) => {
      listCandidates(runId, { signal })
        .then((candidates) => setState({ kind: 'loaded', candidates }))
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === 'AbortError') return
          setState({
            kind: 'error',
            message: error instanceof SipApiError ? error.message : 'Something went wrong. Please try again.',
          })
        })
    },
    [runId],
  )

  useEffect(() => {
    const controller = new AbortController()
    fetchCandidates(controller.signal)
    return () => controller.abort()
  }, [fetchCandidates])

  return (
    <section className="space-y-3" aria-labelledby="candidates-list-heading">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {/* h4, not h3: this screen is always nested inside RunDetailScreen's h3, not a sibling of
            it (unlike CandidateDetailScreen, which replaces RunDetailScreen rather than nesting
            in it). index.css only styles h1-h3 (Big Shoulders, uppercase) — h4 needs its own
            classes here, which it already has. */}
        <h4 id="candidates-list-heading" className="text-sm font-semibold text-inzbc-navy">
          Candidates
        </h4>
        <button
          type="button"
          onClick={() => {
            setState({ kind: 'loading' })
            fetchCandidates()
          }}
          className="min-h-11 rounded-md border border-inzbc-navy/20 px-3 py-2 text-sm font-medium text-inzbc-navy transition-colors hover:border-inzbc-navy/40"
        >
          Refresh
        </button>
      </div>

      {state.kind === 'loading' ? (
        <p role="status" className="text-sm text-slate-600">
          Loading candidates…
        </p>
      ) : null}

      {state.kind === 'error' ? (
        <p role="alert" className="rounded-md border border-inzbc-crimson bg-inzbc-crimson/10 p-3 text-sm text-inzbc-crimson">
          {state.message}
        </p>
      ) : null}

      {state.kind === 'loaded' && state.candidates.length === 0 ? (
        <p className="text-sm text-slate-600">No candidates captured for this run yet.</p>
      ) : null}

      {state.kind === 'loaded' && state.candidates.length > 0 ? (
        <ul className="space-y-2">
          {state.candidates.map((candidate) => (
            <li key={candidate.id} className="rounded-md border border-inzbc-navy/10 bg-white shadow-sm p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-inzbc-navy">{candidate.headline}</p>
                  <p className="mt-1 text-xs text-slate-500">Captured {candidate.captured_at}</p>
                </div>
                <div className="flex flex-wrap gap-1">
                  <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${verificationBadgeClass(candidate.verification)}`}>
                    {candidate.verification}
                  </span>
                  {candidate.signal ? (
                    <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${signalBadgeClass(candidate.signal)}`}>
                      {candidate.signal}
                    </span>
                  ) : null}
                  {candidate.duplicate_of ? (
                    <span className="whitespace-nowrap rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                      Duplicate
                    </span>
                  ) : null}
                </div>
              </div>
              <button
                type="button"
                onClick={() => onSelectCandidate(candidate.id)}
                className="mt-2 min-h-11 rounded-md border border-inzbc-navy/20 px-3 py-2 text-sm font-medium text-inzbc-navy transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
              >
                View and review
              </button>
              <div className="mt-3">
                <CandidateActionPanel candidate={candidate} onUpdated={updateCandidate} />
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
