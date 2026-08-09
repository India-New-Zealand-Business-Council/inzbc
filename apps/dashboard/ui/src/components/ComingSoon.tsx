/**
 * Board measures by module (Membership/Trade-FTA/SIP/Sponsors) per docs/modules/dashboards.md.
 * SIP is the only module with a data source wired up here (SipOverview, #237/#242). The other
 * three depend on issue #47 (dashboards data layer, not started) and their own module's records
 * (modules 3/4) — nothing here is fabricated data, just a clear label for what's not built yet.
 */
const PENDING_MODULES = ['Membership', 'Trade / FTA', 'Sponsors']

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
        {PENDING_MODULES.join(', ')} are not shown here yet. They depend on the dashboards data
        layer (issue #47), which has not been built.
      </p>
    </section>
  )
}
