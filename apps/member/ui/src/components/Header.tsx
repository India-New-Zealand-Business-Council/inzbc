import inzbcLogoAcronymWhite from '../assets/inzbc-logo-acronym-white.svg'

// Navy background + white text per INZBC Brand Guidelines 2026 v1.0 (Colour Palette, p.16) — same
// treatment as apps/comms/ui, apps/sip/ui and apps/fta/ui's headers. Logo: the acronym lockup,
// white variant, sourced from Drive (Brand/Logo Files/Export/SVG - Vector/
// INZBC_Logo_Acronym_White.svg), not fabricated — the guide (p.8) recommends it "at small scales,
// where 'India New Zealand Business Council' might become illegible," exactly this header's use
// case.
//
// "Member Login" links out to Member Jungle rather than rendering a login form: the portal login
// mechanism is undecided (docs/modules/member-portal-spec.md — SSO vs. a separate Member Jungle
// login is an open item, and Wix Members Area itself is only
// "[[proposed — pending INZBC confirmation]]"). Member Jungle is the one system members already
// have real accounts on today — the live site's "Join Now" already redirects to
// inzbc.memberjungle.club (docs/discovery.md) — so linking there is the same link-out-only
// pattern the rest of this shell follows, not a stand-in for a decision nobody has made.
const MEMBER_JUNGLE_URL = 'https://inzbc.memberjungle.club'

const SECTION_LINKS = [
  { href: '#notifications', label: 'Notifications' },
  { href: '#membership', label: 'Membership' },
  { href: '#events', label: 'Events' },
  { href: '#resources', label: 'Resources' },
]

export function Header() {
  return (
    <header className="bg-inzbc-navy text-white">
      <a
        href="#main-content"
        className="sr-only focus-visible:not-sr-only focus-visible:absolute focus-visible:left-4 focus-visible:top-4 focus-visible:z-50 focus-visible:rounded-md focus-visible:bg-white focus-visible:px-3 focus-visible:py-2 focus-visible:text-inzbc-navy"
      >
        Skip to main content
      </a>
      <div className="mx-auto max-w-2xl px-4 py-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-2">
            <a
              href="/"
              className="shrink-0 rounded-sm transition-opacity hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lavender"
            >
              {/* Guide, p.11: acronym logo minimum size is 8mm / 25px wide — h-6 (24px tall)
                  renders this ~81px wide at its native aspect ratio, comfortably above that
                  floor. */}
              <img src={inzbcLogoAcronymWhite} alt="INZBC" className="h-6 w-auto" />
            </a>
            <span aria-hidden="true" className="h-4 w-px shrink-0 bg-white/30" />
            <span className="truncate text-sm font-medium text-white">Member Portal</span>
          </div>
          {/* Tangerine CTA per docs/design-decisions.md: reserved as the accent colour for
              primary actions. Navy text on Tangerine is 5.56:1 (AA pass) — white text on
              Tangerine is only 3.37:1 and fails, the exact bug fixed in PR #162; don't repeat it. */}
          <a
            href={MEMBER_JUNGLE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 rounded-sm bg-inzbc-tangerine px-3 py-1.5 text-sm font-medium text-inzbc-navy transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lavender"
          >
            Member Login
          </a>
        </div>
      </div>
      {/* Horizontally scrollable, not wrapped: four section links plus the logo/CTA row above
          would overflow a 320px viewport if laid out in one row (the failure mode this whole
          commit exists to fix) — same overflow-x-auto tab-strip pattern as
          apps/sip/ui/src/components/AppShell.tsx uses for its (longer) screen switcher. */}
      <nav aria-label="Primary" className="mx-auto max-w-2xl overflow-x-auto px-4 pb-3">
        <ul className="flex gap-4">
          {SECTION_LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="whitespace-nowrap rounded-sm text-sm font-medium text-white/80 transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lavender"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  )
}
