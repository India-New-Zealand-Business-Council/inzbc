import { useEffect, useState } from 'react'
import { getSession, NotSignedInError, type Session } from '../api/session'
import type { ScreenId } from '../types'

interface Props {
  /** Opens a screen and marks onboarding done. */
  onGo: (screen: ScreenId) => void
}

interface Step {
  text: string
  screen: ScreenId
  label: string
}

// What each role can actually do, taken from the roles each write route accepts
// (`write_access(...)` in services/api). A step is only listed here if the server lets that role do
// it, so the walkthrough cannot promise a button that would answer 403.
const ROLE_STEPS: Record<string, { summary: string; steps: Step[] }> = {
  Analyst: {
    summary: 'You run the daily intelligence process up to QA.',
    steps: [
      { text: 'Create a run. Its 24-hour coverage window is fixed when you create it.', screen: 'runs-candidates', label: 'Runs & Candidates' },
      { text: 'Capture, score and route candidates, and record an outcome for every mandatory source.', screen: 'runs-candidates', label: 'Runs & Candidates' },
      { text: 'Open a run and rehearse it with the coordinator agent. It works on a copy, stops at QA and changes nothing.', screen: 'runs-candidates', label: 'Run detail' },
      { text: 'Build the brief against the SIP-185 register and submit it for QA.', screen: 'brief-builder', label: 'Brief Builder' },
    ],
  },
  'SIP Owner': {
    summary: 'You hold launch authority and the CEO ruling.',
    steps: [
      { text: 'Record launch authority and start a run. The agent and pipeline cannot do this for you.', screen: 'runs-candidates', label: 'Runs & Candidates' },
      { text: 'Record the CEO ruling on a report that has passed QA.', screen: 'ceo-decision', label: 'CEO Decision' },
      { text: 'Pause, resume or stop a run when the process needs a person to step in.', screen: 'runs-candidates', label: 'Runs & Candidates' },
    ],
  },
  Reviewer: {
    summary: 'You check other people’s work. You cannot review your own.',
    steps: [
      { text: 'Verify candidate sources. Only a recorded verification lets a High or Critical item into a brief.', screen: 'runs-candidates', label: 'Runs & Candidates' },
      { text: 'Work the SIP-188 QA checklist, then pass, fail or return the run for correction.', screen: 'qa-review', label: 'QA Review' },
      { text: 'Approve reports and Comms drafts that someone else wrote.', screen: 'comms', label: 'Comms Assistant' },
    ],
  },
  Secretariat: {
    summary: 'You draft communications and record distribution.',
    steps: [
      { text: 'Draft member communications. A named reviewer approves every draft before it can be used.', screen: 'comms', label: 'Comms Assistant' },
      { text: 'Record distribution authority and each manual send. Nothing is sent automatically.', screen: 'distribution-status', label: 'Distribution' },
    ],
  },
}

const READ_ONLY_STEPS: Step[] = [
  { text: 'See the four modules and the controls each one enforces.', screen: 'overview', label: 'Overview' },
  { text: 'Read any run, its candidates and its audit trail.', screen: 'runs-candidates', label: 'Runs & Candidates' },
  { text: 'Ask a question about the India–New Zealand FTA. Answers come from a cited corpus, with no model call.', screen: 'fta', label: 'FTA Explainer' },
]

const NEVER = [
  'Publish or distribute anything without a recorded human authority.',
  'Let an AI component cross a human gate. The coordinator agent stops at QA, and 48 of 48 attempts to make it skip a gate were blocked.',
  'Put an unverified High or Critical item into a brief.',
  'Change an audit record. The log is append-only, and human decisions are signed when a signing key is configured.',
]

type SessionState = { kind: 'loading' } | { kind: 'signed-out' } | { kind: 'unavailable' } | { kind: 'loaded'; session: Session }

/**
 * The first screen a new viewer sees: what the platform is for, what their roles let them do
 * here, and what it will never do. Shown once per browser, then reachable from the nav.
 */
export function GettingStartedScreen({ onGo }: Props) {
  const [state, setState] = useState<SessionState>({ kind: 'loading' })

  useEffect(() => {
    let live = true
    getSession()
      .then((session) => live && setState({ kind: 'loaded', session }))
      .catch((error: unknown) => {
        if (live) setState({ kind: error instanceof NotSignedInError ? 'signed-out' : 'unavailable' })
      })
    return () => {
      live = false
    }
  }, [])

  const roles = state.kind === 'loaded' ? state.session.roles : []
  const known = roles.flatMap((role) => {
    const card = ROLE_STEPS[role]
    return card ? [{ role, ...card }] : []
  })

  return (
    <section aria-labelledby="getting-started-heading" className="space-y-6">
      <h2 id="getting-started-heading" className="sr-only">
        Getting started
      </h2>

      <div className="rounded-md border border-inzbc-navy/10 bg-white p-4 shadow-sm">
        {state.kind === 'loading' ? (
          <p role="status" className="text-sm text-slate-600">
            Checking your session…
          </p>
        ) : null}
        {state.kind === 'loaded' ? (
          <p className="text-slate-700">
            Signed in as <strong className="text-inzbc-navy">{state.session.name}</strong>
            {roles.length ? <> · {roles.join(', ')}</> : <> · no roles yet</>}
          </p>
        ) : null}
        {state.kind === 'signed-out' ? (
          <p className="text-slate-700">
            You are not signed in.{' '}
            <a href="/api/auth/github" className="font-medium text-inzbc-blue underline">
              Sign in with GitHub
            </a>{' '}
            to see the steps for your role.
          </p>
        ) : null}
        {state.kind === 'unavailable' ? (
          <p role="alert" className="text-sm text-inzbc-crimson">
            Your session could not be checked, so the steps below are the general ones.
          </p>
        ) : null}
        {state.kind === 'loaded' && roles.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600">
            An administrator has to grant you a role before you can act on anything. You can still read the platform.
          </p>
        ) : null}
      </div>

      {known.map((card) => (
        <RoleCard key={card.role} title={card.role} summary={card.summary} steps={card.steps} onGo={onGo} />
      ))}

      {known.length === 0 ? (
        <RoleCard title="Look around" summary="Everything here can be read by any staff role." steps={READ_ONLY_STEPS} onGo={onGo} />
      ) : null}

      <div className="rounded-md border border-inzbc-navy/10 bg-white p-4 shadow-sm">
        <h3 className="text-base font-semibold text-inzbc-navy">What the platform never does</h3>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
          {NEVER.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </div>

      <button
        type="button"
        onClick={() => onGo('overview')}
        className="min-h-11 rounded-md bg-inzbc-tangerine px-4 py-2 text-sm font-semibold text-inzbc-navy transition-colors hover:bg-inzbc-tangerine/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
      >
        Go to the platform overview
      </button>
    </section>
  )
}

function RoleCard({ title, summary, steps, onGo }: { title: string; summary: string; steps: Step[]; onGo: Props['onGo'] }) {
  return (
    <div className="rounded-md border border-inzbc-navy/10 bg-white p-4 shadow-sm">
      <h3 className="text-base font-semibold text-inzbc-navy">{title}</h3>
      <p className="mt-1 text-sm text-slate-600">{summary}</p>
      <ol className="mt-3 space-y-2">
        {steps.map((step, index) => (
          <li key={step.text} className="flex flex-wrap items-center justify-between gap-2 rounded bg-slate-50 p-2 text-sm">
            <span className="text-slate-700">
              <span className="mr-1 font-semibold text-inzbc-navy">{index + 1}.</span>
              {step.text}
            </span>
            <button
              type="button"
              onClick={() => onGo(step.screen)}
              className="min-h-11 whitespace-nowrap px-2 text-sm font-medium text-inzbc-blue underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
            >
              {step.label} →
            </button>
          </li>
        ))}
      </ol>
    </div>
  )
}
