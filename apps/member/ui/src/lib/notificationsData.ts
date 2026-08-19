// Placeholder rows only — PROJECT-RULES.md: never invent statistics, board names, or FTA details. No
// sourced document lists actual INZBC announcements for this portal, so none are invented; this
// is copy showing the intended layout until a real content source exists.
// In its own module, not exported from NotificationsSection.tsx: a component file that also
// exports a plain constant trips eslint-plugin-react-refresh's only-export-components rule, and
// this way both NotificationsSection and the Dashboard's NotificationsWidget import the same data
// without either one owning it.
export const PLACEHOLDER_NOTIFICATIONS = [
  { id: 'notification-1', date: '[[Date]]', text: '[[Announcement text — pending INZBC content]]' },
  { id: 'notification-2', date: '[[Date]]', text: '[[Announcement text — pending INZBC content]]' },
]
