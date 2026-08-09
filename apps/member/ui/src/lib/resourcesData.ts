export const MEMBER_JUNGLE_URL = 'https://inzbc.memberjungle.club'

// Placeholder rows only — PROJECT-RULES.md: never invent statistics or FTA details. No sourced document
// lists actual trade-guide/FTA-document titles or file locations for this portal; the category
// labels below (not the items) come from apps/site/content/members.md's "Member resources"
// section: "Members-only reports, FTA sector briefings, event recordings, delegation
// opportunities and market-entry resources are available in the member area after sign-in."
// In its own module, not exported from ResourcesSection.tsx: a component file that also exports
// plain constants trips eslint-plugin-react-refresh's only-export-components rule, and this way
// both ResourcesSection and the Dashboard's ResourcesWidget import the same data without either
// one owning it.
export const PLACEHOLDER_RESOURCES = [
  { id: 'resource-1', category: 'FTA sector briefing', title: '[[Document title — pending INZBC resource library]]' },
  { id: 'resource-2', category: 'Trade guide', title: '[[Document title — pending INZBC resource library]]' },
  { id: 'resource-3', category: 'Event recording', title: '[[Document title — pending INZBC resource library]]' },
]
