import { ModuleWelcome } from './ModuleWelcome'

/** The Executive Dashboard's first-visit introduction. */
export function Welcome() {
  return (
    <ModuleWelcome
      storageKey="inzbc.dashboard.welcomed.v1"
      title="How the Executive Dashboard works"
      steps={[
        'The overview shows the current intelligence run, its candidate coverage, the QA and distribution gates and open actions.',
        'Everything is read live from the platform database. An empty panel means there is nothing to show yet, not a fault.',
        'This page only reads. Act on a run from the Trade Intelligence screens in the platform.',
        'Board scorecards for membership, trade and sponsors are not built yet.',
      ]}
    />
  )
}
