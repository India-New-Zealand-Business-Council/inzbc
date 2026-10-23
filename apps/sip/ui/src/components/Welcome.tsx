import { ModuleWelcome } from './ModuleWelcome'

/** Trade Intelligence's first-visit introduction, shown on its five screens. */
export function Welcome() {
  return (
    <ModuleWelcome
      storageKey="inzbc.sip.welcomed.v1"
      title="How Trade Intelligence works"
      steps={[
        'Runs & Candidates: an SIP Owner records launch authority, then an Analyst creates the day’s run and captures, scores and routes candidates.',
        'Brief Builder: the Analyst assembles the brief. Every mandatory source needs a recorded outcome.',
        'QA Review: a Reviewer who is not the run’s analyst works the SIP-188 checklist. A Critical failure blocks release.',
        'CEO Decision, then Distribution: the ruling, approval and distribution authority are separate recorded acts. Nothing is sent automatically.',
      ]}
    />
  )
}
