import { PLACEHOLDER_NOTIFICATIONS } from '../../lib/notificationsData'
import { DashboardCard } from './DashboardCard'

// Reuses the same data as the full NotificationsSection (not a re-declared copy) — see
// src/lib/notificationsData.ts. Shows the first two; the full section below (#notifications) has
// all of them.
export function NotificationsWidget() {
  return (
    <DashboardCard title="Notifications" linkHref="#notifications" linkLabel="View all notifications">
      <ul className="space-y-2">
        {PLACEHOLDER_NOTIFICATIONS.slice(0, 2).map((notification) => (
          <li key={notification.id}>
            <span className="inline-block rounded-sm bg-slate-100 px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-slate-600">
              Placeholder
            </span>
            <p className="mt-1 text-xs text-slate-600">{notification.date}</p>
            <p className="text-sm text-inzbc-navy">{notification.text}</p>
          </li>
        ))}
      </ul>
    </DashboardCard>
  )
}
