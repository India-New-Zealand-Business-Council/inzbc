import { useId, useState } from 'react'
import { isUuid } from '../api/httpClient'
import { CandidateDetailScreen } from './CandidateDetailScreen'
import { RunDetailScreen } from './RunDetailScreen'
import { RunsListScreen } from './RunsListScreen'

type View =
  | { kind: 'runs-list' }
  | { kind: 'run-detail'; runId: string }
  | { kind: 'candidate-detail'; candidateId: string; runId: string }

/**
 * Container for the real, DB-backed Runs/Candidates screens (#237, #242) — a separate area from
 * the four fixture-backed screens AppShell.tsx already manages, since runs/candidates data isn't
 * part of the DailyBriefReport those screens share and nothing about their availability depends
 * on it. Owns two things no individual screen should: which of runs-list / run-detail /
 * candidate-detail is showing, and the single "acting as" id every action call needs.
 *
 * `actor_id`/`initiated_by` are real `users.id` foreign keys (`database/schema.sql`) with no
 * session auth yet (ADR-0004 not implemented) to derive them from — entered once here and passed
 * down, rather than re-entered on every action across four screens.
 */
export function RunsCandidatesScreen() {
  const [view, setView] = useState<View>({ kind: 'runs-list' })
  const [actorId, setActorId] = useState('')
  const actorFieldId = useId()

  const actorIdValid = isUuid(actorId)

  return (
    <section className="space-y-4" aria-labelledby="runs-candidates-heading">
      <div>
        <h2 id="runs-candidates-heading" className="text-lg font-semibold text-inzbc-navy">
          Runs &amp; Candidates
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Live SIP pipeline data (`/api/runs`, `/api/candidates`) — not the fixture-backed screens
          above.
        </p>
      </div>

      <div className="rounded-md border border-inzbc-navy/10 bg-white shadow-sm p-3">
        <label htmlFor={actorFieldId} className="text-xs font-medium text-inzbc-navy">
          Acting as (user id)
        </label>
        <input
          id={actorFieldId}
          type="text"
          value={actorId}
          onChange={(event) => setActorId(event.target.value)}
          placeholder="00000000-0000-0000-0000-000000000000"
          aria-describedby={`${actorFieldId}-hint`}
          className="mt-1 w-full max-w-md rounded-md border border-inzbc-navy/20 p-2 font-mono text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
        />
        <p id={`${actorFieldId}-hint`} className="mt-1 text-xs text-slate-500">
          No session auth exists yet — every action records this id directly. Must be a real{' '}
          <code>users.id</code>; there is no endpoint to look one up from here.
        </p>
        {actorId && !actorIdValid ? (
          <p role="alert" className="mt-1 text-xs text-inzbc-crimson">
            Not a valid id — actions are disabled until this is a well-formed UUID.
          </p>
        ) : null}
      </div>

      {!actorIdValid ? (
        <p role="status" className="text-sm text-slate-600">
          Enter a user id above to enable lifecycle actions. Lists and detail views are still
          visible without one.
        </p>
      ) : null}

      {view.kind === 'runs-list' ? (
        <RunsListScreen actorId={actorId} onSelectRun={(runId) => setView({ kind: 'run-detail', runId })} />
      ) : null}

      {view.kind === 'run-detail' ? (
        <RunDetailScreen
          key={view.runId}
          runId={view.runId}
          actorId={actorId}
          onBack={() => setView({ kind: 'runs-list' })}
          onSelectCandidate={(candidateId) => setView({ kind: 'candidate-detail', candidateId, runId: view.runId })}
        />
      ) : null}

      {view.kind === 'candidate-detail' ? (
        <CandidateDetailScreen
          key={view.candidateId}
          candidateId={view.candidateId}
          actorId={actorId}
          onBack={() => setView({ kind: 'run-detail', runId: view.runId })}
        />
      ) : null}
    </section>
  )
}
