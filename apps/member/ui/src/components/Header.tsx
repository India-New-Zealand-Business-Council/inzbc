import { ArrowUpRight } from 'lucide-react'

// Floating glass-pill header, matching the live inzview build
// (India-New-Zealand-Business-Council/inzview, src/components/inzbc/motion.tsx's StickyHeader) —
// same treatment as apps/fta/ui's and apps/comms/ui's Header.tsx. The four section anchors take
// inzview's centre nav-link slot; Member Login takes its "Join INZBC" CTA slot.
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
    <header className="pointer-events-none fixed inset-x-0 top-0 z-50 p-4 sm:p-5">
      <a
        href="#main-content"
        className="sr-only focus-visible:not-sr-only focus-visible:pointer-events-auto focus-visible:absolute focus-visible:left-4 focus-visible:top-4 focus-visible:z-50 focus-visible:rounded-md focus-visible:bg-white focus-visible:px-3 focus-visible:py-2 focus-visible:text-inzbc-ink"
      >
        Skip to main content
      </a>
      <div className="pointer-events-auto relative mx-auto flex w-full max-w-7xl min-h-[64px] items-center justify-between gap-4 rounded-[1.2rem] border border-white/60 bg-white/80 px-4 py-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.78),0_18px_60px_rgba(9,3,24,0.14)] backdrop-blur-2xl backdrop-saturate-150">
        <div className="flex shrink-0 items-center gap-2">
          <a
            href="/"
            className="inline-flex min-h-11 items-center rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lime"
          >
            <img src={LOGO_URL} alt="INZBC" className="h-auto w-[clamp(120px,16vw,150px)]" />
          </a>
          <span aria-hidden="true" className="h-4 w-px bg-inzbc-ink/20" />
          <span className="hidden text-sm font-medium text-inzbc-ink sm:inline">Member Portal</span>
        </div>
        <nav aria-label="Primary" className="overflow-x-auto">
          <ul className="flex gap-1">
            {SECTION_LINKS.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  className="inline-flex min-h-11 items-center whitespace-nowrap rounded-md px-3 text-sm font-medium text-inzbc-ink/70 transition-colors hover:text-inzbc-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lime"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        {/* Lime CTA, matching inzview's own bg-lime/text-navy button convention (Sections.tsx,
            InnerPage.tsx) rather than the Brand Guidelines' Tangerine accent this used to be.
            Navy text on Lime is a comfortable AA pass, same reasoning as the Tangerine version
            this replaces (docs/design-decisions.md; the white-on-Tangerine failure from PR #162
            doesn't recur here since text stays navy). */}
        <a
          href={MEMBER_JUNGLE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex min-h-11 shrink-0 items-center gap-1.5 rounded-full bg-inzbc-lime px-4 py-2.5 text-sm font-semibold text-inzbc-navy transition-transform active:scale-[0.97] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lime"
        >
          Member Login
          <ArrowUpRight aria-hidden="true" size={16} />
        </a>
      </div>
    </header>
  )
}
