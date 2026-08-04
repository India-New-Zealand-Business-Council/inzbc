import { MEMBER_JUNGLE_EVENTS_URL, PLACEHOLDER_EVENTS } from '../../lib/eventsData'
import { DashboardCard } from './DashboardCard'

// Reuses the same data as the full EventsSection (not a re-declared copy) — see
// src/lib/eventsData.ts. Shows the next two; the full section below (#events) has the rest and
// the per-event Register links.
export function EventsWidget() {
  return (
    <DashboardCard title="Upcoming Events" linkHref="#events" linkLabel="View all events">
      <ul className="space-y-2">
        {PLACEHOLDER_EVENTS.slice(0, 2).map((event) => (
          <li key={event.id}>
            <span className="inline-block rounded-sm bg-slate-100 px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-slate-600">
              Placeholder
            </span>
            <p className="mt-1 text-sm font-medium text-inzbc-navy">{event.name}</p>
            <p className="text-xs text-slate-600">{event.date}</p>
          </li>
        ))}
      </ul>
      {/* Also a direct calendar link, not just the "view all" link to #events below: the full
          section's per-event Register buttons all point here too, so a member skimming the
          dashboard can reach registration in one click rather than two. */}
      <a
        href={MEMBER_JUNGLE_EVENTS_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-2 inline-block text-xs font-medium text-inzbc-blue underline decoration-inzbc-blue/40 underline-offset-2 hover:decoration-inzbc-blue focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
      >
        Full calendar on Member Jungle
      </a>
    </DashboardCard>
  )
}
