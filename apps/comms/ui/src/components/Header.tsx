import { ArrowUpRight } from 'lucide-react'

// Floating glass-pill header, matching the live inzview build
// (India-New-Zealand-Business-Council/inzview, src/components/inzbc/motion.tsx's StickyHeader)
// rather than the flat solid-navy bar this used to be. Simplified from that component: inzview's
// version is multi-page (react-router links, a collapsing mobile menu) — this app is a single
// page, so there's no link list to collapse and no router to depend on. The logo URL is the same
// one inzview's content.ts uses, pulled straight from the Wix Media Manager — sourced, not
// re-hosted, so it stays in sync with whatever INZBC uploads there.
const LOGO_URL = 'https://static.wixstatic.com/media/df219d_0b8e6333d53841efaf66f675038a0798~mv2.jpg'

export function Header() {
  return (
    // pointer-events-none on the wrapper + pointer-events-auto on the pill (inzview's own
    // pattern): the fixed strip spans the full viewport width, but only the pill itself should
    // ever intercept a click — everything outside it passes through to the page beneath.
    <header className="pointer-events-none fixed inset-x-0 top-0 z-50 p-4 sm:p-5">
      <a
        href="#main-content"
        className="sr-only focus-visible:not-sr-only focus-visible:pointer-events-auto focus-visible:absolute focus-visible:left-4 focus-visible:top-4 focus-visible:z-50 focus-visible:rounded-md focus-visible:bg-white focus-visible:px-3 focus-visible:py-2 focus-visible:text-inzbc-ink"
      >
        Skip to main content
      </a>
      <div className="pointer-events-auto relative mx-auto flex w-full max-w-2xl min-h-[64px] items-center justify-between gap-4 rounded-[1.2rem] border border-white/60 bg-white/80 px-4 py-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.78),0_18px_60px_rgba(9,3,24,0.14)] backdrop-blur-2xl backdrop-saturate-150">
        <a
          href="/"
          className="inline-flex min-h-11 items-center rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lime"
        >
          <img src={LOGO_URL} alt="INZBC" className="h-auto w-[clamp(120px,16vw,150px)]" />
        </a>
        <nav aria-label="Primary" className="flex items-center">
          <span
            aria-current="page"
            className="border-b-2 border-inzbc-lime pb-0.5 text-sm font-medium text-inzbc-ink"
          >
            Comms Assistant
          </span>
        </nav>
        <a
          href="https://inzbc.memberjungle.club/index.cfm?module=membership_v2&kat=add_register"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden min-h-11 items-center gap-1.5 rounded-full bg-inzbc-ink px-4 py-2.5 text-sm font-semibold text-white transition-transform active:scale-[0.97] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lime sm:inline-flex"
        >
          Join INZBC
          <ArrowUpRight aria-hidden="true" size={16} />
        </a>
      </div>
    </header>
  )
}
