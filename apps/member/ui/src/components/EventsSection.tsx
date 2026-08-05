import { MEMBER_JUNGLE_EVENTS_URL, PLACEHOLDER_EVENTS } from '../lib/eventsData'

// Registration platform framing per docs/client-answers.md C6/C7 and apps/site/content/events.md:
// "Member Jungle is the normal registration platform; Zoho only where a major event needs
// functions Member Jungle cannot provide." Both proposals are still `[[proposed — pending INZBC
// confirmation]]`. This section links out per event rather than running registration itself —
// docs/modules/member-portal-spec.md's build gate: "the portal's 'trade opportunities' screen
// should link to registration on whichever platform the event uses — it doesn't run registration
// itself."
export function EventsSection() {
  return (
    <section id="events" aria-labelledby="events-heading" className="mt-10">
      <h2 id="events-heading" className="text-xl text-inzbc-navy sm:text-2xl">
        Upcoming Events
      </h2>
      <p className="mt-2 text-slate-700">
        Registration happens on Member Jungle, or on Zoho for the small number of events that need
        something Member Jungle can&apos;t provide. Each event links to whichever platform it
        actually uses — this portal doesn&apos;t run registration itself.
      </p>

      <ul className="mt-4 space-y-3">
        {PLACEHOLDER_EVENTS.map((event) => (
          <li
            key={event.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 bg-white p-4"
          >
            <div>
              {/* text-slate-600, not -500: -500 on bg-slate-100 is ~4.34:1, below the 4.5:1
                  minimum for this 12px text (SC 1.4.3) — -600 clears it at ~7:1. */}
              <span className="inline-block rounded-sm bg-slate-100 px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-slate-600">
                Placeholder
              </span>
              <p className="mt-1 font-medium text-inzbc-navy">{event.name}</p>
              <p className="text-sm text-slate-600">{event.date}</p>
            </div>
            {/* Blue, not Lavender, for the focus ring: this button sits on the white card
                background, not Header's navy — lavender-on-white is ~1.6:1, failing the 3:1
                non-text-contrast minimum (SC 1.4.11). Blue-on-white is ~15:1. */}
            <a
              href={MEMBER_JUNGLE_EVENTS_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-sm bg-inzbc-tangerine px-3 py-1.5 text-sm font-medium text-inzbc-navy transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
            >
              Register
            </a>
          </li>
        ))}
      </ul>

      <a
        href={MEMBER_JUNGLE_EVENTS_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-4 inline-block rounded-sm text-sm font-medium text-inzbc-blue underline decoration-inzbc-blue/40 underline-offset-2 hover:decoration-inzbc-blue focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
      >
        View the full event calendar on Member Jungle
      </a>
    </section>
  )
}
