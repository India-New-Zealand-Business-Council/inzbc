import { useCallback, useEffect, useState } from 'react'
import { getCandidate, type CandidateOut, SipApiError } from '../api/candidatesClient'
import { CandidateActionPanel } from '../components/CandidateActionPanel'
import { signalBadgeClass, verificationBadgeClass } from '../lib/candidateState'

interface Props {
  candidateId: string
  /** UUID of the acting user — see RunsListScreen.tsx's Props doc for why this is caller-supplied. */
  actorId: string
  onBack: () => void
}

type LoadState = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'loaded'; candidate: CandidateOut }

/**
 * One candidate's full detail (`GET /api/candidates/:id`) plus the four commands
 * (`CandidateActionPanel`, shared with CandidatesListScreen).
 *
 * Like RunDetailScreen.tsx, callers must render this with `key={candidateId}` so a change of
 * selected candidate remounts rather than needing an effect-triggered `setState` reset — see that
 * file's Props doc for why.
 */
export function CandidateDetailScreen({ candidateId, actorId, onBack }: Props) {
  const [state, setState] = useState<LoadState>({ kind: 'loading' })

  const fetchCandidate = useCallback(
    (signal?: AbortSignal) => {
      getCandidate(candidateId, { signal })
        .then((candidate) => setState({ kind: 'loaded', candidate }))
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === 'AbortError') return
          setState({
            kind: 'error',
            message: error instanceof SipApiError ? error.message : 'Something went wrong. Please try again.',
          })
        })
    },
    [candidateId],
  )

  useEffect(() => {
    const controller = new AbortController()
    fetchCandidate(controller.signal)
    return () => controller.abort()
  }, [fetchCandidate])

  return (
    <section className="space-y-4" aria-labelledby="candidate-detail-heading">
      <button
        type="button"
        onClick={onBack}
        className="min-h-11 px-1 text-sm font-medium text-inzbc-blue underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
      >
        ← Back to run
      </button>

      {state.kind === 'loading' ? (
        <p role="status" className="text-sm text-slate-600">
          Loading candidate…
        </p>
      ) : null}

      {state.kind === 'error' ? (
        <p role="alert" className="rounded-md border border-inzbc-crimson bg-inzbc-crimson/10 p-3 text-sm text-inzbc-crimson">
          {state.message}
        </p>
      ) : null}

      {state.kind === 'loaded' ? (
        <div className="rounded-md border border-inzbc-navy/10 bg-white shadow-sm p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              {/* h3, not h2: nested under RunsCandidatesScreen's h2 "Runs & Candidates" — this
                  screen replaces RunDetailScreen (a sibling h3), it doesn't nest inside it. */}
              <h3 id="candidate-detail-heading" className="text-lg font-semibold text-inzbc-navy">
                {state.candidate.headline}
              </h3>
              <p className="mt-1 text-xs text-slate-500">{state.candidate.id}</p>
            </div>
            <div className="flex flex-wrap gap-1">
              <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${verificationBadgeClass(state.candidate.verification)}`}>
                {state.candidate.verification}
              </span>
              {state.candidate.signal ? (
                <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${signalBadgeClass(state.candidate.signal)}`}>
                  {state.candidate.signal}
                </span>
              ) : null}
            </div>
          </div>

          {state.candidate.summary ? <p className="mt-2 text-sm text-slate-700">{state.candidate.summary}</p> : null}

          {state.candidate.url ? (
            <p className="mt-2 text-sm">
              <a href={state.candidate.url} target="_blank" rel="noopener noreferrer" className="text-inzbc-blue underline">
                {state.candidate.url}
              </a>
            </p>
          ) : null}

          <dl className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs text-slate-500">Run</dt>
              <dd className="break-all text-slate-700">{state.candidate.run_id}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Source</dt>
              <dd className="break-all text-slate-700">{state.candidate.source_id ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Captured</dt>
              <dd className="text-slate-700">{state.candidate.captured_at}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Published</dt>
              <dd className="text-slate-700">{state.candidate.published_at ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">In coverage window</dt>
              <dd className="text-slate-700">
                {state.candidate.in_coverage_window === null ? '—' : state.candidate.in_coverage_window ? 'Yes' : 'No'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Source confidence</dt>
              <dd className="text-slate-700">{state.candidate.confidence ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">NZ / India / Member relevance</dt>
              <dd className="text-slate-700">
                {state.candidate.nz_relevance ?? '—'} / {state.candidate.india_relevance ?? '—'} /{' '}
                {state.candidate.member_relevance ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Included</dt>
              <dd className="text-slate-700">
                {state.candidate.included === null ? '—' : state.candidate.included ? 'Yes' : 'No'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Proposed routing</dt>
              <dd className="text-slate-700">{state.candidate.proposed_routing ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Duplicate of</dt>
              <dd className="break-all text-slate-700">{state.candidate.duplicate_of ?? '—'}</dd>
            </div>
          </dl>

          {state.candidate.reason ? (
            <p className="mt-3 text-xs text-slate-500">
              <span className="font-medium text-inzbc-navy">Last recorded reason:</span> {state.candidate.reason}
            </p>
          ) : null}

          <div className="mt-4">
            <CandidateActionPanel
              candidate={state.candidate}
              actorId={actorId}
              onUpdated={(updated) => setState({ kind: 'loaded', candidate: updated })}
            />
          </div>
        </div>
      ) : null}
    </section>
  )
}
