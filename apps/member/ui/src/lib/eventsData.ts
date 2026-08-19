export const MEMBER_JUNGLE_EVENTS_URL = 'https://inzbc.memberjungle.club'

// Placeholder rows only — PROJECT-RULES.md: never invent event names, dates or details. The one real,
// sourced event name in the repo is "INZBC Summit" (docs/client-answers.md D8 — "India Unplugged
// Summit" appears in no sourced document and must not be used), but no sourced document gives it
// a confirmed date, so even that name isn't used here as if it were a scheduled listing.
// In its own module, not exported from EventsSection.tsx: a component file that also exports
// plain constants trips eslint-plugin-react-refresh's only-export-components rule, and this way
// both EventsSection and the Dashboard's EventsWidget import the same data without either one
// owning it.
export const PLACEHOLDER_EVENTS = [
  { id: 'event-1', name: '[[Event name — pending INZBC event calendar]]', date: '[[Date]]' },
  { id: 'event-2', name: '[[Event name — pending INZBC event calendar]]', date: '[[Date]]' },
]
