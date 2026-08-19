// In its own module, not exported from MembershipSection.tsx: a component file that also exports
// plain constants trips eslint-plugin-react-refresh's only-export-components rule, and this way
// both MembershipSection and the Dashboard's MembershipWidget import the same data without either
// one owning it.
export const MEMBER_JUNGLE_URL = 'https://inzbc.memberjungle.club'

// Every action links to the same Member Jungle root domain — no sourced document gives distinct
// sub-paths for join/renew vs. directory vs. billing, so this doesn't invent one.
//
// Sourced per apps/site/content/members.md: "Join Now and renewals are managed on Member Jungle
// (inzbc.memberjungle.club). The website links out; membership records are not duplicated here."
// and "Link out to the Member Jungle directory rather than embedding a second copy: Member Jungle
// is the membership system of record and the register must not exist in two places. Opt-in fields
// only." Also docs/client-answers.md C1 (retain-and-integrate, no second membership register) and
// C5 (link, don't copy/embed the directory) — both `[[proposed — pending INZBC confirmation]]`,
// and PROJECT-RULES.md's standing rule: do not rebuild membership on Wix before the retain/integrate/
// replace assessment; link out, do not duplicate.
export const MEMBERSHIP_ACTIONS = [
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
