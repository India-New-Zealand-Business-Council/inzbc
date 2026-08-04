import { useId, type ReactNode } from 'react'

// Shared shell for the four Dashboard summary widgets — one place for the card chrome and the
// "view full section" link pattern, so each widget's own commit only adds its content, not a
// re-declaration of the same border/padding/link styling four times.
//
// role="group" + aria-labelledby: without it, a screen reader user tabbing through the grid has
// no signal of where one card's content ends and the next begins — four cards' worth of links
// would announce as one undifferentiated list. useId, not a title-derived slug, for the same
// reason apps/sip/ui's BriefBuilderScreen uses it: guaranteed-unique regardless of what two
// widgets happen to be titled.
export function DashboardCard({
  title,
  linkHref,
  linkLabel,
  children,
}: {
  title: string
  linkHref: string
  linkLabel: string
  children: ReactNode
}) {
  const titleId = useId()
  return (
    <div
      role="group"
      aria-labelledby={titleId}
      className="flex h-full flex-col rounded-md border border-slate-200 bg-white p-4 shadow-sm"
    >
      <h3 id={titleId} className="text-sm font-semibold text-inzbc-navy">
        {title}
      </h3>
      <div className="mt-2 flex-1 space-y-2">{children}</div>
      {/* Blue, not Lavender: this link sits on the white card background, not Header's navy —
          lavender-on-white is ~1.6:1, failing the 3:1 non-text-contrast minimum (SC 1.4.11).
          Blue-on-white is ~15:1 — same reasoning as the tangerine buttons elsewhere in this app.
          py-1 -mx-1 px-1: a bare text-sm line is ~20px tall, under the 24px WCAG 2.5.8 minimum
          tap-target size — this pads the hit area without changing the visible spacing (the
          negative margin cancels the added horizontal padding). */}
      <a
        href={linkHref}
        className="-mx-1 mt-3 inline-block rounded-sm px-1 py-1 text-sm font-medium text-inzbc-blue underline decoration-inzbc-blue/40 underline-offset-2 hover:decoration-inzbc-blue focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
      >
        {linkLabel}
      </a>
    </div>
  )
}
