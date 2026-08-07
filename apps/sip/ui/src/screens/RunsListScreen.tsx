import { useCallback, useEffect, useId, useState } from 'react'
import { listRuns, nextAction, type RunOut, SipApiError } from '../api/runsClient'
import { RUN_ACTION_LABEL as ACTION_LABEL, RUN_APPROVAL_REF_LABEL as APPROVAL_REF_LABEL, submitRunAction } from '../lib/runActions'
import { stateBadgeClass } from '../lib/runState'

interface Props {
  /** UUID of the acting user (`database/schema.sql`: `initiated_by`/`actor_id` are real `users`
   * foreign keys, no session auth exists to derive this from yet — see httpClient.ts's isUuid). */
  actorId: string
  onSelectRun: (runId: string) => void
}

type LoadState = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'loaded'; runs: RunOut[] }

type ActionState = { kind: 'idle' } | { kind: 'loading' } | { kind: 'error'; message: string }


/** Runs list (#237): fetches on mount, and every lifecycle action (start/pause/resume/complete). */
export function RunsListScreen({ actorId, onSelectRun }: Props) {
  const [state, setState] = useState<LoadState>({ kind: 'loading' })
  // Only one run's action panel open at a time, mirroring QaReviewScreen's editingId pattern.
  const [openRunId, setOpenRunId] = useState<string | null>(null)
  const [reason, setReason] = useState('')
  const [approvalRef, setApprovalRef] = useState('')
  const [actionState, setActionState] = useState<ActionState>({ kind: 'idle' })
  const formId = useId()

  // Split from `reload` below so the mount effect never calls setState synchronously within its
  // own body (react-hooks/set-state-in-effect) — the effect only starts the fetch; every state
  // update happens inside the promise's .then/.catch, which is not "within the effect" for that
  // rule's purposes. The initial `useState({kind: 'loading'})` above already covers the mount
  // case, so nothing needs to set it again on first render.
  const fetchRuns = useCallback((signal?: AbortSignal) => {
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
    fetchRuns(controller.signal)
    return () => controller.abort()
  }, [fetchRuns])

  /** For the Refresh button and after a successful action — a real user event, not an effect, so
   * setting the loading state synchronously here before re-fetching is fine. */
  function reload() {
    setState({ kind: 'loading' })
    fetchRuns()
  }

  function openAction(runId: string) {
    setOpenRunId(openRunId === runId ? null : runId)
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
      await submitRunAction(action, run.id, body)
      setOpenRunId(null)
      setActionState({ kind: 'idle' })
      reload()
    } catch (error) {
      setActionState({
        kind: 'error',
        message: error instanceof SipApiError ? error.message : 'Something went wrong. Please try again.',
      })
    }
  }

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
          onClick={reload}
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
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => onSelectRun(run.id)}
                  className="min-h-11 rounded-md border border-inzbc-navy/20 px-3 py-2 text-sm font-medium text-inzbc-navy transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
                >
                  View run and candidates
                </button>
                {nextAction(run.state) ? (
                  <button
                    type="button"
                    aria-expanded={openRunId === run.id}
                    onClick={() => openAction(run.id)}
                    className="min-h-11 rounded-md bg-inzbc-tangerine px-3 py-2 text-sm font-semibold text-inzbc-navy transition-colors hover:enabled:bg-inzbc-tangerine/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
                  >
                    {ACTION_LABEL[nextAction(run.state)!]}
                  </button>
                ) : null}
              </div>

              {openRunId === run.id && nextAction(run.state) ? (
                (() => {
                  const action = nextAction(run.state)!
                  return (
                    <form
                      className="mt-3 space-y-2 rounded-md border border-inzbc-navy/10 bg-slate-50 p-3"
                      onSubmit={(event) => {
                        event.preventDefault()
                        void confirmAction(run, action)
                      }}
                    >
                      <div>
                        <label htmlFor={`${formId}-reason-${run.id}`} className="text-xs font-medium text-inzbc-navy">
                          Reason
                        </label>
                        <input
                          id={`${formId}-reason-${run.id}`}
                          type="text"
                          value={reason}
                          onChange={(event) => setReason(event.target.value)}
                          className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                        />
                      </div>
                      {action !== 'complete' ? (
                        <div>
                          <label htmlFor={`${formId}-approval-${run.id}`} className="text-xs font-medium text-inzbc-navy">
                            {APPROVAL_REF_LABEL[action]}
                          </label>
                          <input
                            id={`${formId}-approval-${run.id}`}
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
                          onClick={() => openAction(run.id)}
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
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
