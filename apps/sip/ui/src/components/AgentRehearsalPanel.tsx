import { useCallback, useEffect, useRef, useState } from 'react'
import { listRehearsals, type RehearsalOut, SipApiError, startRehearsal } from '../api/runsClient'

interface Props {
  runId: string
  /** The run's state. A rehearsal needs recorded launch authority, so a Draft run cannot have one. */
  runState: string
}

type ListState = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'loaded'; items: RehearsalOut[] }
type StartState = { kind: 'idle' } | { kind: 'running' } | { kind: 'error'; message: string }

const OUTCOME_LABEL: Record<string, string> = {
  reached_qa: 'Stopped at the QA gate',
  stopped: 'Stopped early',
}

const SEAL_LABEL: Record<string, string> = {
  valid: 'Seal verified',
  invalid: 'Seal does not verify',
  unsealed: 'Not sealed (no signing key)',
  'key-not-configured': 'Sealed; key not available to check',
}

function message(error: unknown): string {
  return error instanceof SipApiError ? error.message : 'Something went wrong. Please try again.'
}

function trustworthy(r: RehearsalOut): boolean {
  return r.verification.chain_intact && r.verification.replay === 'exact' && r.verification.seal !== 'invalid'
}

/**
 * Run the coordinator agent from the app (`POST /api/runs/:id/agent-rehearsals`) and read back
 * each rehearsal's sealed trail.
 *
 * A rehearsal is advisory: the agent works on a copy of the run and stops at the QA gate, so
 * nothing here changes the run above it. The server re-checks every trail when it is read (chain
 * head, seal, replay with no model call), and this panel shows that result rather than trusting
 * the stored outcome on its own.
 */
export function AgentRehearsalPanel({ runId, runState }: Props) {
  const [list, setList] = useState<ListState>({ kind: 'loading' })
  const [start, setStart] = useState<StartState>({ kind: 'idle' })
  const [openId, setOpenId] = useState<string | null>(null)
  // One request in flight at a time, same reasoning as ExecutiveOverview's fetchDashboard: Refresh
  // aborts the previous one so a slower older response can never overwrite a newer one, and
  // unmounting aborts whatever is still pending.
  const inFlight = useRef<AbortController | null>(null)

  const fetchRehearsals = useCallback(() => {
    inFlight.current?.abort()
    const controller = new AbortController()
    inFlight.current = controller
    listRehearsals(runId, { signal: controller.signal })
      .then((items) => {
        if (!controller.signal.aborted) setList({ kind: 'loaded', items })
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setList({ kind: 'error', message: message(error) })
      })
  }, [runId])

  useEffect(() => {
    fetchRehearsals()
    return () => inFlight.current?.abort()
  }, [fetchRehearsals])

  function refresh() {
    setList({ kind: 'loading' })
    fetchRehearsals()
  }

  async function run() {
    setStart({ kind: 'running' })
    try {
      const created = await startRehearsal(runId)
      setList((current) => ({
        kind: 'loaded',
        items: [created, ...(current.kind === 'loaded' ? current.items : [])],
      }))
      setOpenId(created.id)
      setStart({ kind: 'idle' })
    } catch (error) {
      setStart({ kind: 'error', message: message(error) })
    }
  }

  const launchRecorded = runState !== 'Draft'

  return (
    <section aria-labelledby={`rehearsals-${runId}`} className="rounded-md border border-inzbc-navy/10 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 id={`rehearsals-${runId}`} className="text-base font-semibold text-inzbc-navy">
            Coordinator agent
          </h4>
          <p className="mt-1 max-w-prose text-sm text-slate-600">
            Rehearse this run with the AI coordinator. It works on a copy, proposes one step at a time, and stops at the
            QA gate. This run, its candidates and its source checks are not changed.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={refresh}
            disabled={list.kind === 'loading'}
            className="min-h-11 rounded-md border border-inzbc-navy/20 px-3 py-2 text-sm font-medium text-inzbc-navy transition-colors hover:enabled:border-inzbc-navy/40 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
          >
            Refresh
          </button>
          <button
            type="button"
            onClick={() => void run()}
            disabled={!launchRecorded || start.kind === 'running'}
            className="min-h-11 rounded-md bg-inzbc-tangerine px-3 py-2 text-sm font-semibold text-inzbc-navy transition-colors hover:enabled:bg-inzbc-tangerine/90 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
          >
            {start.kind === 'running' ? 'Running agent…' : 'Run the agent'}
          </button>
        </div>
      </div>

      {!launchRecorded ? (
        <p className="mt-2 text-sm text-slate-600">A SIP Owner has to start the run (record launch authority) first.</p>
      ) : null}

      {start.kind === 'error' ? (
        <p role="alert" className="mt-3 rounded-md border border-inzbc-crimson bg-inzbc-crimson/10 p-3 text-sm text-inzbc-crimson">
          {start.message}
        </p>
      ) : null}

      {list.kind === 'loading' ? (
        <p role="status" className="mt-3 text-sm text-slate-600">
          Loading rehearsals…
        </p>
      ) : null}
      {list.kind === 'error' ? (
        <p role="alert" className="mt-3 text-sm text-inzbc-crimson">
          {list.message}
        </p>
      ) : null}
      {list.kind === 'loaded' && list.items.length === 0 ? (
        <p className="mt-3 text-sm text-slate-600">No rehearsals yet.</p>
      ) : null}

      {list.kind === 'loaded' && list.items.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {list.items.map((r) => {
            const open = openId === r.id
            return (
              <li key={r.id} className="rounded-md border border-inzbc-navy/10">
                <button
                  type="button"
                  aria-expanded={open}
                  onClick={() => setOpenId(open ? null : r.id)}
                  className="flex min-h-11 w-full flex-wrap items-center justify-between gap-2 p-3 text-left text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                >
                  <span className="font-medium text-inzbc-navy">
                    {OUTCOME_LABEL[r.outcome] ?? r.outcome} · {r.final_state}
                  </span>
                  <span className="text-xs text-slate-500">
                    {r.accepted} accepted, {r.refused} refused · {new Date(r.started_at).toLocaleString()}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      trustworthy(r) ? 'bg-emerald-100 text-emerald-800' : 'bg-inzbc-crimson/10 text-inzbc-crimson'
                    }`}
                  >
                    {trustworthy(r) ? 'Trail verified' : 'Trail check failed'}
                  </span>
                </button>
                {open ? (
                  <div className="space-y-3 border-t border-inzbc-navy/10 p-3 text-sm">
                    {r.stop_reason ? (
                      <p>
                        <span className="font-medium text-inzbc-navy">Why it stopped: </span>
                        <span className="break-words text-slate-700">{r.stop_reason}</span>
                      </p>
                    ) : null}
                    {r.brief_summary ? (
                      <p>
                        <span className="font-medium text-inzbc-navy">Draft brief: </span>
                        <span className="text-slate-700">{r.brief_summary}</span>
                      </p>
                    ) : null}
                    <dl className="grid grid-cols-1 gap-1 sm:grid-cols-3">
                      <div>
                        <dt className="text-xs text-slate-500">Hash chain</dt>
                        <dd>{r.verification.chain_intact ? 'Intact' : 'Broken'}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-slate-500">Seal</dt>
                        <dd>{SEAL_LABEL[r.verification.seal] ?? r.verification.seal}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-slate-500">Replay (no model call)</dt>
                        <dd className="break-words">{r.verification.replay === 'exact' ? 'Exact' : r.verification.replay}</dd>
                      </div>
                    </dl>
                    <ol className="space-y-1" aria-label="Agent steps">
                      {r.tool_steps.map((step) => (
                        <li key={step.sequence} className="rounded bg-slate-50 p-2">
                          <div className="flex flex-wrap justify-between gap-2">
                            <code className="text-xs text-inzbc-navy">
                              {step.sequence + 1}. {step.tool}
                            </code>
                            <span className={`text-xs font-medium ${step.outcome === 'refused' ? 'text-inzbc-crimson' : 'text-emerald-700'}`}>
                              {step.outcome === 'refused' ? 'Refused' : 'Accepted'}
                            </span>
                          </div>
                          <p className="text-xs text-slate-600">{step.reason}</p>
                          <p className="break-words text-xs text-slate-500">
                            {step.state_before} → {step.state_after}: {step.detail}
                          </p>
                        </li>
                      ))}
                    </ol>
                  </div>
                ) : null}
              </li>
            )
          })}
        </ul>
      ) : null}
    </section>
  )
}
