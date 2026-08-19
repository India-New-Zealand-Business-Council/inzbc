import { Container } from './Container'

// Navy background + white text, matching the live inzview build's header colour
// (India-New-Zealand-Business-Council/inzview uses lime as its one accent throughout — applied
// below to the login CTA and focus rings, replacing the old tangerine/lavender pairing). Not
// rebuilt as inzview's floating glass-pill nav (see apps/fta/ui's and apps/comms/ui's
// Header.tsx): that pattern fits a single-row marketing nav, not this header's two rows (logo/CTA
// plus a horizontally-scrollable section-link strip) — docking it in normal flow keeps those
// links reliably visible instead of floating over section content they anchor-link into. Logo:
// pulled from the same Wix Media asset inzview's content.ts uses, not the old locally-committed
// SVG.
//
// "Member Login" links out to Member Jungle rather than rendering a login form: the portal login
// mechanism is undecided (docs/modules/member-portal-spec.md — SSO vs. a separate Member Jungle
// login is an open item, and Wix Members Area itself is only
// "[[proposed — pending INZBC confirmation]]"). Member Jungle is the one system members already
// have real accounts on today — the live site's "Join Now" already redirects to
// inzbc.memberjungle.club (docs/discovery.md) — so linking there is the same link-out-only
// pattern the rest of this shell follows, not a stand-in for a decision nobody has made.
const MEMBER_JUNGLE_URL = 'https://inzbc.memberjungle.club'

const LOGO_URL = 'https://static.wixstatic.com/media/df219d_0b8e6333d53841efaf66f675038a0798~mv2.jpg'

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
      <Container className="py-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-2">
            <a
              href="/"
              className="shrink-0 rounded-sm transition-opacity hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lime"
            >
              <img src={LOGO_URL} alt="INZBC" className="h-6 w-auto" />
            </a>
            <span aria-hidden="true" className="h-4 w-px shrink-0 bg-white/30" />
            <span className="truncate text-sm font-medium text-white">Member Portal</span>
          </div>
          {/* Lime CTA, matching inzview's own bg-lime/text-navy button convention (Sections.tsx,
              InnerPage.tsx) rather than the Brand Guidelines' Tangerine accent this used to be.
              Navy text on Lime is a comfortable AA pass, same reasoning as the Tangerine version
              this replaces (docs/design-decisions.md; the white-on-Tangerine failure from PR #162
              doesn't recur here since text stays navy). */}
          <a
            href={MEMBER_JUNGLE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 rounded-sm bg-inzbc-lime px-3 py-1.5 text-sm font-medium text-inzbc-navy transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lime"
          >
            Member Login
          </a>
        </div>
      </Container>
      {/* Horizontally scrollable, not wrapped: four section links plus the logo/CTA row above
          would overflow a 320px viewport if laid out in one row (the failure mode this whole
          commit exists to fix) — same overflow-x-auto tab-strip pattern as
          apps/sip/ui/src/components/AppShell.tsx uses for its (longer) screen switcher. Same
          max-w-7xl/padding as Container by hand, not the component itself: Container renders a
          <div>, and this needs to be the <nav> element for its own aria-label. */}
      <nav aria-label="Primary" className="mx-auto max-w-7xl overflow-x-auto px-4 pb-3 sm:px-6 lg:px-8">
        <ul className="flex gap-4">
          {SECTION_LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="whitespace-nowrap rounded-sm text-sm font-medium text-white/80 transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lime"
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
