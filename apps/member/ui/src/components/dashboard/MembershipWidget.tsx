import { MEMBER_JUNGLE_URL, MEMBERSHIP_ACTIONS } from '../../lib/membershipData'
import { DashboardCard } from './DashboardCard'

// Reuses the same data and the same Member Jungle link as the full MembershipSection (not a
// re-declared copy) — see src/lib/membershipData.ts. Every action link goes straight to Member
// Jungle, same as the full section; "view all" here goes to the full section for the
// description text each action carries there.
export function MembershipWidget() {
  return (
    <DashboardCard title="Membership" linkHref="#membership" linkLabel="View membership details">
      <ul className="space-y-2">
        {MEMBERSHIP_ACTIONS.map((action) => (
          <li key={action.id}>
            {/* -mx-1 px-1 py-1: pads the tap target to WCAG 2.5.8's 24px minimum without
                changing the visible spacing between list items (the negative margin cancels the
                added horizontal padding). */}
            <a
              href={MEMBER_JUNGLE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="-mx-1 inline-block px-1 py-1 text-sm font-medium text-inzbc-navy underline decoration-inzbc-navy/30 underline-offset-2 hover:decoration-inzbc-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
            >
              {action.label}
            </a>
          </li>
        ))}
      </ul>
    </DashboardCard>
  )
}
