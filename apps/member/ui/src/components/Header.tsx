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

export function Header() {
  return (
    <header className="bg-inzbc-navy text-white">
      <a
        href="#main-content"
        className="sr-only focus-visible:not-sr-only focus-visible:absolute focus-visible:left-4 focus-visible:top-4 focus-visible:z-50 focus-visible:rounded-md focus-visible:bg-white focus-visible:px-3 focus-visible:py-2 focus-visible:text-inzbc-navy"
      >
        Skip to main content
      </a>
      <div className="mx-auto flex max-w-2xl items-center justify-between px-4 py-4">
        <a
          href="/"
          className="rounded-sm transition-opacity hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lavender"
        >
          {/* Guide, p.11: acronym logo minimum size is 8mm / 25px wide — h-6 (24px tall) renders
              this ~81px wide at its native aspect ratio, comfortably above that floor. */}
          <img src={inzbcLogoAcronymWhite} alt="INZBC" className="h-6 w-auto" />
        </a>
        <nav aria-label="Primary" className="flex items-center gap-4">
          {/* Lavender, not Blue, for the current-page accent: Blue #261866 on this header's Navy
              #160933 is ~1.5:1 contrast, unreadable — same reasoning as the sibling apps' headers. */}
          <span aria-current="page" className="border-b-2 border-inzbc-lavender text-sm font-medium text-white">
            Member Portal
          </span>
          <a
            href="#events"
            className="rounded-sm text-sm font-medium text-white/80 transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lavender"
          >
            Events
          </a>
          {/* Tangerine CTA per docs/design-decisions.md: reserved as the accent colour for
              primary actions. Navy text on Tangerine is 5.56:1 (AA pass) — white text on
              Tangerine is only 3.37:1 and fails, the exact bug fixed in PR #162; don't repeat it. */}
          <a
            href={MEMBER_JUNGLE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-sm bg-inzbc-tangerine px-3 py-1.5 text-sm font-medium text-inzbc-navy transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lavender"
          >
            Member Login
          </a>
        </nav>
      </div>
    </header>
  )
}
