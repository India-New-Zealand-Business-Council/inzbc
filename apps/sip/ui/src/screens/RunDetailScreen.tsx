import { useCallback, useEffect, useId, useState } from 'react'
import { getRun, nextAction, type RunOut, SipApiError } from '../api/runsClient'
import { RUN_ACTION_LABEL as ACTION_LABEL, RUN_APPROVAL_REF_LABEL as APPROVAL_REF_LABEL, submitRunAction } from '../lib/runActions'
import { stateBadgeClass } from '../lib/runState'

interface Props {
  runId: string
  /** UUID of the acting user — see RunsListScreen.tsx's Props doc for why this is caller-supplied. */
  actorId: string
  onBack: () => void
}

type LoadState = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'loaded'; run: RunOut }

type ActionState = { kind: 'idle' } | { kind: 'loading' } | { kind: 'error'; message: string }

/**
 * One run's full detail (`GET /api/runs/:id`) plus its own lifecycle action, mirroring
 * RunsListScreen.tsx's action panel. Candidates for this run render below it — see the next
 * commit; this one is the run's own info only.
 *
 * Callers must render this with `key={runId}` (the container screen wired up in a later commit
 * does). That forces a full remount — a fresh `useState({kind: 'loading'})` — when the selected
 * run changes, rather than this component tracking `runId` changes itself: the natural
 * alternative, resetting to 'loading' inside the fetch effect when `runId` changes, calls
 * setState synchronously in a way react-hooks/set-state-in-effect traces through even one level
 * of function indirection (unlike RunsListScreen.tsx's fetch, which only ever runs once and never
 * needs that reset).
 */
export function RunDetailScreen({ runId, actorId, onBack }: Props) {
  const [state, setState] = useState<LoadState>({ kind: 'loading' })
  const [actionOpen, setActionOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [approvalRef, setApprovalRef] = useState('')
  const [actionState, setActionState] = useState<ActionState>({ kind: 'idle' })
  const formId = useId()

  const fetchRun = useCallback(
    (signal?: AbortSignal) => {
      getRun(runId, { signal })
        .then((run) => setState({ kind: 'loaded', run }))
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
    fetchRun(controller.signal)
    return () => controller.abort()
  }, [fetchRun])

  function openAction() {
    setActionOpen((open) => !open)
    setReason('')
    setApprovalRef('')
    setActionState({ kind: 'idle' })
  }

  async function confirmAction(run: RunOut, action: 'start' | 'pause' | 'resume' | 'complete') {
    if (!reason.trim()) {
      setActionState({ kind: 'error', message: 'A reason is required.' })
      return
    }
    if (action !== 'complete' && !approvalRef.trim()) {
      setActionState({ kind: 'error', message: `${APPROVAL_REF_LABEL[action]} is required.` })
      return
    }
    setActionState({ kind: 'loading' })
    const body = {
      expected_version: run.version,
      actor_id: actorId,
      reason: reason.trim(),
      approval_ref: action === 'complete' ? null : approvalRef.trim(),
    }
    try {
      const updated = await submitRunAction(action, run.id, body)
      setState({ kind: 'loaded', run: updated })
      setActionOpen(false)
      setActionState({ kind: 'idle' })
    } catch (error) {
      setActionState({
        kind: 'error',
        message: error instanceof SipApiError ? error.message : 'Something went wrong. Please try again.',
      })
    }
  }

  return (
    <section className="space-y-4" aria-labelledby="run-detail-heading">
      <button
        type="button"
        onClick={onBack}
        className="min-h-11 px-1 text-sm font-medium text-inzbc-blue underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
      >
        ← Back to runs
      </button>

      {state.kind === 'loading' ? (
        <p role="status" className="text-sm text-slate-600">
          Loading run…
        </p>
      ) : null}

      {state.kind === 'error' ? (
        <p role="alert" className="rounded-md border border-inzbc-crimson bg-inzbc-crimson/10 p-3 text-sm text-inzbc-crimson">
          {state.message}
        </p>
      ) : null}

      {state.kind === 'loaded' ? (
        <>
          <div className="rounded-md border border-inzbc-navy/10 bg-white shadow-sm p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h2 id="run-detail-heading" className="text-lg font-semibold text-inzbc-navy">
                  {state.run.run_number}
                </h2>
                <p className="mt-1 text-xs text-slate-500">{state.run.id}</p>
              </div>
              <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${stateBadgeClass(state.run.state)}`}>
                {state.run.state}
              </span>
            </div>
            <dl className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-xs text-slate-500">Coverage window</dt>
                <dd className="text-slate-700">
                  {state.run.coverage_start_utc} – {state.run.coverage_end_utc}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Prompt version</dt>
                <dd className="text-slate-700">{state.run.prompt_version}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Version (optimistic concurrency)</dt>
                <dd className="text-slate-700">{state.run.version}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Initiated by</dt>
                <dd className="break-all text-slate-700">{state.run.initiated_by}</dd>
              </div>
            </dl>

            {nextAction(state.run.state) ? (
              <div className="mt-4">
                <button
                  type="button"
                  aria-expanded={actionOpen}
                  onClick={openAction}
                  className="min-h-11 rounded-md bg-inzbc-tangerine px-3 py-2 text-sm font-semibold text-inzbc-navy transition-colors hover:enabled:bg-inzbc-tangerine/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
                >
                  {ACTION_LABEL[nextAction(state.run.state)!]}
                </button>

                {actionOpen
                  ? (() => {
                      const action = nextAction(state.run.state)!
                      const run = state.run
                      return (
                        <form
                          className="mt-3 space-y-2 rounded-md border border-inzbc-navy/10 bg-slate-50 p-3"
                          onSubmit={(event) => {
                            event.preventDefault()
                            void confirmAction(run, action)
                          }}
                        >
                          <div>
                            <label htmlFor={`${formId}-reason`} className="text-xs font-medium text-inzbc-navy">
                              Reason
                            </label>
                            <input
                              id={`${formId}-reason`}
                              type="text"
                              value={reason}
                              onChange={(event) => setReason(event.target.value)}
                              className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                            />
                          </div>
                          {action !== 'complete' ? (
                            <div>
                              <label htmlFor={`${formId}-approval`} className="text-xs font-medium text-inzbc-navy">
                                {APPROVAL_REF_LABEL[action]}
                              </label>
                              <input
                                id={`${formId}-approval`}
                                type="text"
                                value={approvalRef}
                                onChange={(event) => setApprovalRef(event.target.value)}
                                className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                              />
                            </div>
                          ) : null}
                          <div className="flex flex-wrap items-center gap-2">
                            <button
                              type="submit"
                              disabled={actionState.kind === 'loading'}
                              className="min-h-11 rounded-md bg-inzbc-tangerine px-3 py-2 text-sm font-semibold text-inzbc-navy disabled:cursor-progress disabled:opacity-60"
                            >
                              {actionState.kind === 'loading' ? 'Submitting…' : `Confirm ${ACTION_LABEL[action]}`}
                            </button>
                            <button
                              type="button"
                              onClick={openAction}
                              className="min-h-11 px-2 text-sm font-medium text-inzbc-blue underline"
                            >
                              Cancel
                            </button>
                          </div>
                          {actionState.kind === 'error' ? (
                            <p role="alert" className="text-sm text-inzbc-crimson">
                              {actionState.message}
                            </p>
                          ) : null}
                        </form>
                      )
                    })()
                  : null}
              </div>
            ) : null}
          </div>
        </>
      ) : null}
    </section>
  )
}
