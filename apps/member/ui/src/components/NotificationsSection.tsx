import { PLACEHOLDER_NOTIFICATIONS } from '../lib/notificationsData'

export function NotificationsSection() {
  return (
    <section id="notifications" aria-labelledby="notifications-heading" className="mt-10">
      <h2 id="notifications-heading" className="text-xl text-inzbc-navy sm:text-2xl">
        Notifications
      </h2>
      <p className="mt-2 text-slate-800">Recent INZBC updates and announcements.</p>

      <ul className="mt-4 space-y-3">
        {PLACEHOLDER_NOTIFICATIONS.map((notification) => (
          <li key={notification.id} className="rounded-md border border-slate-200 bg-white p-4">
            {/* text-slate-600, not -500: -500 on bg-slate-100 is ~4.34:1, below the 4.5:1
                minimum for this 12px text (SC 1.4.3) — -600 clears it at ~7:1. */}
            <span className="inline-block rounded-sm bg-slate-100 px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-slate-600">
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
