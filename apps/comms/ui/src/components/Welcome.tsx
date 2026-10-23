import { ModuleWelcome } from './ModuleWelcome'

/** The Comms Assistant's first-visit introduction. */
export function Welcome() {
  return (
    <ModuleWelcome
      storageKey="inzbc.comms.welcomed.v1"
      title="How the Comms Assistant works"
      steps={[
        'Pick the content type: newsletter, LinkedIn post, event announcement or member spotlight.',
        'Fill in a short brief: the topic, up to eight key points, any links and the tone. Do not include member personal data.',
        'Generate a draft, and generate again if it needs another pass. You can download it as Word or PDF.',
        'A named reviewer who is not the author approves the draft. Nothing here sends or publishes anything.',
      ]}
    />
  )
}
