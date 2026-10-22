/**
 * Board / measures scorecards by module (docs/modules/dashboards.md's "Board / measures"
 * section), distinct from the executive view above (#61/#47, now built). Each scorecard needs
 * its own module's records (membership applications, FTA enquiries, sponsor benefits) — none of
 * that exists yet, so nothing here is fabricated data, just a clear label for what's not built.
 */
const PENDING_MODULES = ['Membership', 'Trade / FTA', 'SIP scorecard', 'Sponsors / governance']

export function ComingSoon() {
  return (
    <section
      className="rounded-md border border-dashed border-inzbc-navy/30 bg-white p-4"
      aria-labelledby="coming-soon-heading"
    >
      <h2 id="coming-soon-heading" className="text-lg font-semibold text-inzbc-navy">
        Coming soon
      </h2>
      <p className="mt-2 text-sm text-slate-700">
        Board scorecards for {PENDING_MODULES.join(', ')} are not shown here yet — each depends on
        its own module's records, which don't exist yet.
      </p>
    </section>
  )
}
