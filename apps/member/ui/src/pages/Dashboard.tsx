import { EventsWidget } from '../components/dashboard/EventsWidget'
import { MembershipWidget } from '../components/dashboard/MembershipWidget'
import { NotificationsWidget } from '../components/dashboard/NotificationsWidget'
import { ResourcesWidget } from '../components/dashboard/ResourcesWidget'

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

      {/* 1 column on mobile, 2 at sm (tablet), 4 at lg (desktop/laptop) — matches the Container's
          own breakpoints so the grid fills the widened layout rather than leaving it looking like
          a narrow single column stretched across a wide page. */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <NotificationsWidget />
        <MembershipWidget />
        <EventsWidget />
        <ResourcesWidget />
      </div>
    </section>
  )
}
