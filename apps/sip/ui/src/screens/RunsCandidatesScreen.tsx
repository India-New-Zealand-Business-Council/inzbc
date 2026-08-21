import { useState } from 'react'
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
 * on it. Owns just which of runs-list / run-detail / candidate-detail is showing.
 *
 * No "acting as" id here (or anywhere in this screen tree): every write endpoint derives identity
 * from the session (#278) and rejects a caller-supplied `actor_id`/`initiated_by` outright
 * (`extra="forbid"` on every request model) rather than silently ignoring it. `vitest.setup.ts`
 * seeds a session before each test, matching what the real API now expects.
 */
export function RunsCandidatesScreen() {
  const [view, setView] = useState<View>({ kind: 'runs-list' })

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

      {view.kind === 'runs-list' ? (
        <RunsListScreen onSelectRun={(runId) => setView({ kind: 'run-detail', runId })} />
      ) : null}

      {view.kind === 'run-detail' ? (
        <RunDetailScreen
          key={view.runId}
          runId={view.runId}
          onBack={() => setView({ kind: 'runs-list' })}
          onSelectCandidate={(candidateId) => setView({ kind: 'candidate-detail', candidateId, runId: view.runId })}
        />
      ) : null}

      {view.kind === 'candidate-detail' ? (
        <CandidateDetailScreen
          key={view.candidateId}
          candidateId={view.candidateId}
          onBack={() => setView({ kind: 'run-detail', runId: view.runId })}
        />
      ) : null}
    </section>
  )
}
