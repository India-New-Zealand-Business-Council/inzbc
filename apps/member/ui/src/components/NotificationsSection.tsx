// Placeholder rows only — CLAUDE.md: never invent statistics, board names, or FTA details. No
// sourced document lists actual INZBC announcements for this portal, so none are invented; this
// is copy showing the intended layout until a real content source exists.
const PLACEHOLDER_NOTIFICATIONS = [
  { id: 'notification-1', date: '[[Date]]', text: '[[Announcement text — pending INZBC content]]' },
  { id: 'notification-2', date: '[[Date]]', text: '[[Announcement text — pending INZBC content]]' },
]

export function NotificationsSection() {
  return (
    <section id="notifications" aria-labelledby="notifications-heading" className="mt-10">
      <h2 id="notifications-heading" className="text-xl text-inzbc-navy sm:text-2xl">
        Notifications
      </h2>
      <p className="mt-2 text-slate-700">Recent INZBC updates and announcements.</p>

      <ul className="mt-4 space-y-3">
        {PLACEHOLDER_NOTIFICATIONS.map((notification) => (
          <li key={notification.id} className="rounded-md border border-slate-200 bg-white p-4">
            <span className="inline-block rounded-sm bg-slate-100 px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-slate-500">
              Placeholder
            </span>
            <p className="mt-1 text-sm text-slate-600">{notification.date}</p>
            <p className="text-inzbc-navy">{notification.text}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
