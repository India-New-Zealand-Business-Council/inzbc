const MEMBER_JUNGLE_URL = 'https://inzbc.memberjungle.club'

// Placeholder rows only — CLAUDE.md: never invent statistics or FTA details. No sourced document
// lists actual trade-guide/FTA-document titles or file locations for this portal; the category
// labels below (not the items) come from apps/site/content/members.md's "Member resources"
// section: "Members-only reports, FTA sector briefings, event recordings, delegation
// opportunities and market-entry resources are available in the member area after sign-in."
const PLACEHOLDER_RESOURCES = [
  { id: 'resource-1', category: 'FTA sector briefing', title: '[[Document title — pending INZBC resource library]]' },
  { id: 'resource-2', category: 'Trade guide', title: '[[Document title — pending INZBC resource library]]' },
  { id: 'resource-3', category: 'Event recording', title: '[[Document title — pending INZBC resource library]]' },
]

// Resources stay on Member Jungle rather than being hosted/downloaded from this shell:
// docs/modules/member-portal-spec.md's build gate treats any screen that displays real member-
// only content as not buildable until the retain/integrate/replace assessment lands. This section
// is copy plus a link out, like Events and the Member Jungle integration section.
export function ResourcesSection() {
  return (
    <section id="resources" aria-labelledby="resources-heading" className="mt-10">
      <h2 id="resources-heading" className="text-xl text-inzbc-navy sm:text-2xl">
        Resources
      </h2>
      <p className="mt-2 text-slate-700">
        Members-only reports, FTA sector briefings, event recordings, delegation opportunities and
        market-entry resources are available after signing in on Member Jungle.
      </p>

      <ul className="mt-4 space-y-3">
        {PLACEHOLDER_RESOURCES.map((resource) => (
          <li
            key={resource.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 bg-white p-4"
          >
            <div>
              <span className="inline-block rounded-sm bg-slate-100 px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                Placeholder
              </span>
              <p className="mt-1 text-xs font-medium uppercase tracking-wide text-inzbc-forest">
                {resource.category}
              </p>
              <p className="text-inzbc-navy">{resource.title}</p>
            </div>
            <a
              href={MEMBER_JUNGLE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-sm bg-inzbc-tangerine px-3 py-1.5 text-sm font-medium text-inzbc-navy transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lavender"
            >
              Sign in to view
            </a>
          </li>
        ))}
      </ul>
    </section>
  )
}
