import { MEMBER_JUNGLE_URL, MEMBERSHIP_ACTIONS } from '../lib/membershipData'

export function MembershipSection() {
  return (
    <section id="membership" aria-labelledby="membership-heading" className="mt-10">
      <h2 id="membership-heading" className="text-xl text-inzbc-navy sm:text-2xl">
        Membership
      </h2>
      <p className="mt-2 text-slate-700">
        Member Jungle is INZBC&apos;s membership system of record. Membership, billing and the
        member directory are managed there, not duplicated on this portal.
      </p>

      <ul className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {MEMBERSHIP_ACTIONS.map((action) => (
          <li key={action.id} className="rounded-md border border-slate-200 bg-white p-4">
            <p className="font-medium text-inzbc-navy">{action.label}</p>
            <p className="mt-1 text-sm text-slate-600">{action.description}</p>
            {/* Blue, not Lavender, for the focus ring: this button sits on the white card
                background, not Header's navy — lavender-on-white is ~1.6:1, failing the 3:1
                non-text-contrast minimum (SC 1.4.11). Blue-on-white is ~15:1. */}
            <a
              href={MEMBER_JUNGLE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-block rounded-sm bg-inzbc-tangerine px-3 py-1.5 text-sm font-medium text-inzbc-navy transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
            >
              Continue on Member Jungle
            </a>
          </li>
        ))}
      </ul>
    </section>
  )
}
