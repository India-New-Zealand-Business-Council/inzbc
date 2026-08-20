import { useState } from 'react'
import type { DailyBriefReport } from '../domain'
import { newDraftReportFixture } from '../lib/fixtures'
import { BriefBuilderScreen } from '../screens/BriefBuilderScreen'
import { CeoDecisionScreen } from '../screens/CeoDecisionScreen'
import { DistributionStatusScreen } from '../screens/DistributionStatusScreen'
import { QaReviewScreen } from '../screens/QaReviewScreen'
import { SCREENS, type ScreenId } from '../types'
import { Footer } from './Footer'

const LOGO_URL = 'https://static.wixstatic.com/media/df219d_0b8e6333d53841efaf66f675038a0798~mv2.jpg'

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
      {/* Floating glass-pill header, matching the live inzview build
          (India-New-Zealand-Business-Council/inzview, src/components/inzbc/motion.tsx's
          StickyHeader) — same treatment as apps/fta/ui's and apps/comms/ui's Header.tsx. The
          4-tab screen switcher takes the centre nav slot inzview's page links use; there's no
          "Join INZBC"-equivalent action for a staff tool, so the right-hand CTA slot is dropped
          rather than filled with something that doesn't belong here. Logo: pulled from the same
          Wix Media asset inzview's content.ts uses, not the old locally-committed SVG. */}
      <header className="pointer-events-none fixed inset-x-0 top-0 z-50 p-4 sm:p-5">
        <a
          href="#main-content"
          className="sr-only focus-visible:not-sr-only focus-visible:pointer-events-auto focus-visible:absolute focus-visible:left-4 focus-visible:top-4 focus-visible:z-50 focus-visible:rounded-md focus-visible:bg-white focus-visible:px-3 focus-visible:py-2 focus-visible:text-inzbc-ink"
        >
          Skip to main content
        </a>
        <div className="pointer-events-auto relative mx-auto flex w-full max-w-7xl min-h-[64px] items-center justify-between gap-4 rounded-[1.2rem] border border-white/60 bg-white/80 px-4 py-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.78),0_18px_60px_rgba(9,3,24,0.14)] backdrop-blur-2xl backdrop-saturate-150">
          <div className="flex shrink-0 items-center gap-2">
            <img src={LOGO_URL} alt="INZBC" className="h-auto w-[clamp(120px,16vw,150px)]" />
            <span aria-hidden="true" className="h-4 w-px bg-inzbc-ink/20" />
            <span className="hidden text-sm font-medium text-inzbc-ink sm:inline">SIP Review</span>
          </div>
          <nav aria-label="Screens" className="overflow-x-auto">
            <ul className="flex gap-1">
              {SCREENS.map((option) => (
                <li key={option.id}>
                  <button
                    type="button"
                    aria-current={screen === option.id ? 'page' : undefined}
                    onClick={() => setScreen(option.id)}
                    className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lime ${
                      screen === option.id
                        ? 'border-inzbc-lime text-inzbc-ink'
                        : 'border-transparent text-inzbc-ink/60 hover:text-inzbc-ink'
                    }`}
                  >
                    {option.label}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>

      {/* pt-24/pt-28 clears the fixed floating header above — it no longer sits in normal flow,
          so the page has to make its own room for it. */}
      <main id="main-content" className="mx-auto w-full max-w-7xl flex-1 px-4 pb-6 pt-24 sm:pt-28">
        <div className="mb-6">
          <h1 className="text-2xl font-extrabold text-inzbc-navy sm:text-3xl">SIP Review</h1>
          <p className="mt-2 text-slate-700">
            Staff review and approval for the Trade Intelligence Platform's daily brief — brief
            builder, QA, CEO decision, distribution status (docs/sip-ui-spec.md).
          </p>
        </div>
        {screen === 'brief-builder' ? <BriefBuilderScreen report={report} onChange={setReport} /> : null}
        {screen === 'qa-review' ? <QaReviewScreen report={report} onChange={setReport} /> : null}
        {screen === 'ceo-decision' ? <CeoDecisionScreen report={report} onChange={setReport} /> : null}
        {screen === 'distribution-status' ? <DistributionStatusScreen report={report} /> : null}
      </main>
      <Footer />
    </div>
  )
}
