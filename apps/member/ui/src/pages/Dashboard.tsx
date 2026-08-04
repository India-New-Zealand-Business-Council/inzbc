import { NotificationsWidget } from '../components/dashboard/NotificationsWidget'

// The main overview screen — members see everything at a glance in one place. Not a routed page
// (no router exists anywhere in this codebase, and this app has exactly one screen): a distinct
// page-level component App.tsx renders above the existing full Notifications/Membership/Events/
// Resources sections, which stay unchanged below it. Widgets here are compact summaries that link
// down to those full sections via the same in-page anchors (#notifications, #membership, #events,
// #resources) Header's nav already uses.
export function Dashboard() {
  return (
    <section aria-labelledby="dashboard-heading" className="mb-10">
      <h2 id="dashboard-heading" className="text-xl text-inzbc-navy sm:text-2xl">
        Overview
      </h2>
      <p className="mt-2 text-slate-700">
        Notifications, membership, upcoming events and resources at a glance.
      </p>

      <div className="mt-4">
        <NotificationsWidget />
      </div>
    </section>
  )
}
