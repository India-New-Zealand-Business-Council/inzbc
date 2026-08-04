import type { ReactNode } from 'react'

// Shared shell for the four Dashboard summary widgets — one place for the card chrome and the
// "view full section" link pattern, so each widget's own commit only adds its content, not a
// re-declaration of the same border/padding/link styling four times.
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
  return (
    <div className="flex h-full flex-col rounded-md border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-inzbc-navy">{title}</h3>
      <div className="mt-2 flex-1 space-y-2">{children}</div>
      {/* Blue, not Lavender: this link sits on the white card background, not Header's navy —
          lavender-on-white is ~1.6:1, failing the 3:1 non-text-contrast minimum (SC 1.4.11).
          Blue-on-white is ~15:1 — same reasoning as the tangerine buttons elsewhere in this app. */}
      <a
        href={linkHref}
        className="mt-3 inline-block rounded-sm text-sm font-medium text-inzbc-blue underline decoration-inzbc-blue/40 underline-offset-2 hover:decoration-inzbc-blue focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
      >
        {linkLabel}
      </a>
    </div>
  )
}
