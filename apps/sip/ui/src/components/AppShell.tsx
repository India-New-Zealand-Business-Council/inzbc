import { useState } from 'react'
import inzbcLogoAcronymWhite from '../assets/inzbc-logo-acronym-white.svg'
import type { DailyBriefReport } from '../domain'
import { newDraftReportFixture } from '../lib/fixtures'
import { BriefBuilderScreen } from '../screens/BriefBuilderScreen'
import { CeoDecisionScreen } from '../screens/CeoDecisionScreen'
import { DistributionStatusScreen } from '../screens/DistributionStatusScreen'
import { QaReviewScreen } from '../screens/QaReviewScreen'
import { SCREENS, type ScreenId } from '../types'
import { Footer } from './Footer'

// A 4-screen internal tool with no deep-linking requirement in docs/sip-ui-spec.md — plain state
// avoids a router dependency for something this small. `report` is the one run moving through
// the four screens in this session; it is lifted here (rather than fetched independently by each
// screen) because later screens' availability depends on this same report's state
// (schemas/state-machine.md — e.g. the CEO decision screen isn't reachable until QA has passed).
export function AppShell() {
  const [screen, setScreen] = useState<ScreenId>('brief-builder')
  const [report, setReport] = useState<DailyBriefReport>(() => newDraftReportFixture())

  return (
    // flex-col + flex-1 on main (not min-h-screen on main alone) so the footer sits at the
    // bottom of short pages without overlapping content on tall ones — same sticky-footer
    // layout as apps/comms/ui's App.tsx.
    <div className="flex min-h-screen flex-col bg-slate-50">
      {/* Navy background + white text per INZBC Brand Guidelines 2026 v1.0 (Colour Palette,
          p.16) — same treatment as apps/comms/ui's Header, so the two staff tools share one
          visual language. Logo: the acronym lockup, white variant, sourced from Drive (Brand/
          Logo Files/Export/SVG - Vector/INZBC_Logo_Acronym_White.svg), not fabricated — the
          guide (p.8) recommends it "at small scales, where 'India New Zealand Business Council'
          might become illegible," exactly this header's use case. */}
      <header className="bg-inzbc-navy text-white">
        <a
          href="#main-content"
          className="sr-only focus-visible:not-sr-only focus-visible:absolute focus-visible:left-4 focus-visible:top-4 focus-visible:z-50 focus-visible:rounded-md focus-visible:bg-white focus-visible:px-3 focus-visible:py-2 focus-visible:text-inzbc-navy"
        >
          Skip to main content
        </a>
        <div className="mx-auto max-w-4xl px-4 py-4 sm:py-6">
          <div className="flex items-center gap-2">
            {/* Guide, p.11: acronym logo minimum size is 8mm / 25px wide — h-6 (24px tall)
                renders this ~81px wide at its native aspect ratio, above that floor. */}
            <img src={inzbcLogoAcronymWhite} alt="INZBC" className="h-6 w-auto" />
            <span aria-hidden="true" className="h-4 w-px bg-white/30" />
            {/* font-family/weight/uppercase come from the h1 rule in index.css's @layer base. */}
            <h1 className="text-xl text-white sm:text-2xl">SIP Review</h1>
          </div>
          <p className="mt-1 text-sm text-white/80">
            Staff review and approval for the Trade Intelligence Platform's daily brief — brief
            builder, QA, CEO decision, distribution status (docs/sip-ui-spec.md).
          </p>
        </div>
        <nav aria-label="Screens" className="mx-auto max-w-4xl overflow-x-auto px-4">
          <ul className="flex gap-1">
            {SCREENS.map((option) => (
              <li key={option.id}>
                <button
                  type="button"
                  aria-current={screen === option.id ? 'page' : undefined}
                  onClick={() => setScreen(option.id)}
                  // Lavender, not the index.css base rule's default Blue: Blue #261866 on this
                  // header's Navy #160933 is ~1.5:1 contrast, unreadable — same reasoning as
                  // apps/comms/ui's Header nav accent.
                  className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lavender ${
                    screen === option.id
                      ? 'border-inzbc-tangerine text-white'
                      : 'border-transparent text-white/70 hover:text-white'
                  }`}
                >
                  {option.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <main id="main-content" className="mx-auto w-full max-w-4xl flex-1 px-4 py-6">
        {screen === 'brief-builder' ? <BriefBuilderScreen report={report} onChange={setReport} /> : null}
        {screen === 'qa-review' ? <QaReviewScreen report={report} onChange={setReport} /> : null}
        {screen === 'ceo-decision' ? <CeoDecisionScreen report={report} onChange={setReport} /> : null}
        {screen === 'distribution-status' ? <DistributionStatusScreen report={report} /> : null}
      </main>
      <Footer />
    </div>
  )
}
