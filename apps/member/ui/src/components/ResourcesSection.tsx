import { MEMBER_JUNGLE_URL, PLACEHOLDER_RESOURCES } from '../lib/resourcesData'

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
              {/* text-slate-600, not -500: -500 on bg-slate-100 is ~4.34:1, below the 4.5:1
                  minimum for this 12px text (SC 1.4.3) — -600 clears it at ~7:1. */}
              <span className="inline-block rounded-sm bg-slate-100 px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-slate-600">
                Placeholder
              </span>
              <p className="mt-1 text-xs font-medium uppercase tracking-wide text-inzbc-forest">
                {resource.category}
              </p>
              <p className="text-inzbc-navy">{resource.title}</p>
            </div>
            {/* Blue, not Lavender, for the focus ring: this button sits on the white card
                background, not Header's navy — lavender-on-white is ~1.6:1, failing the 3:1
                non-text-contrast minimum (SC 1.4.11). Blue-on-white is ~15:1. */}
            <a
              href={MEMBER_JUNGLE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-sm bg-inzbc-tangerine px-3 py-1.5 text-sm font-medium text-inzbc-navy transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
            >
              Sign in to view
            </a>
          </li>
        ))}
      </ul>
    </section>
  )
}
