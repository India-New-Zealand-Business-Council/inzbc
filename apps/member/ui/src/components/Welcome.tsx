import { ModuleWelcome } from './ModuleWelcome'

/** The Member Portal's first-visit introduction. */
export function Welcome() {
  return (
    <ModuleWelcome
      storageKey="inzbc.member.welcomed.v1"
      title="Welcome to the Member Portal"
      steps={[
        'The overview gathers your notifications, membership, upcoming events and resources.',
        'Membership, billing and the member directory stay on Member Jungle. Links take you there rather than copying your details here.',
        'Further down, the notifications, membership, events and resources sections give the detail behind each card.',
      ]}
    />
  )
}
