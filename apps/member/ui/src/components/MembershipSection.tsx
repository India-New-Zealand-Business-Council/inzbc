const MEMBER_JUNGLE_URL = 'https://inzbc.memberjungle.club'

// Every action here redirects to the same Member Jungle root domain — no sourced document gives
// distinct sub-paths for join/renew vs. directory vs. billing, so this doesn't invent one.
//
// Sourced per apps/site/content/members.md: "Join Now and renewals are managed on Member Jungle
// (inzbc.memberjungle.club). The website links out; membership records are not duplicated here."
// and "Link out to the Member Jungle directory rather than embedding a second copy: Member Jungle
// is the membership system of record and the register must not exist in two places. Opt-in fields
// only." Also docs/client-answers.md C1 (retain-and-integrate, no second membership register) and
// C5 (link, don't copy/embed the directory) — both `[[proposed — pending INZBC confirmation]]`,
// and CLAUDE.md's standing rule: do not rebuild membership on Wix before the retain/integrate/
// replace assessment; link out, do not duplicate.
const MEMBERSHIP_ACTIONS = [
  {
    id: 'join-renew',
    label: 'Join / Renew',
    description: 'Start a new membership or renew an existing one.',
  },
  {
    id: 'directory',
    label: 'Member Directory',
    description: "Browse the directory, or manage your own listing's opt-in visibility.",
  },
  {
    id: 'billing',
    label: 'Billing & Invoices',
    description: 'View invoices and receipts, or update payment details.',
  },
]

export function MembershipSection() {
  return (
    <section id="membership" aria-labelledby="membership-heading" className="mt-10">
      <h2 id="membership-heading" className="text-xl text-inzbc-navy sm:text-2xl">
        Membership
      </h2>
      <p className="mt-2 text-slate-700">
        Member Jungle is INZBC&apos;s membership system of record. Membership, billing and the
        member directory are managed there, not duplicated on this portal.
      </p>

      <ul className="mt-4 grid gap-3 sm:grid-cols-3">
        {MEMBERSHIP_ACTIONS.map((action) => (
          <li key={action.id} className="rounded-md border border-slate-200 bg-white p-4">
            <p className="font-medium text-inzbc-navy">{action.label}</p>
            <p className="mt-1 text-sm text-slate-600">{action.description}</p>
            <a
              href={MEMBER_JUNGLE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-block rounded-sm bg-inzbc-tangerine px-3 py-1.5 text-sm font-medium text-inzbc-navy transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lavender"
            >
              Continue on Member Jungle
            </a>
          </li>
        ))}
      </ul>
    </section>
  )
}
