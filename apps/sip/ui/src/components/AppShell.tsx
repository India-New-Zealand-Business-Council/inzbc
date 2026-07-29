import { useState } from 'react'
import type { DailyBriefReport } from '../domain'
import { newDraftReportFixture } from '../lib/fixtures'
import { BriefBuilderScreen } from '../screens/BriefBuilderScreen'
import { CeoDecisionScreen } from '../screens/CeoDecisionScreen'
import { DistributionStatusScreen } from '../screens/DistributionStatusScreen'
import { QaReviewScreen } from '../screens/QaReviewScreen'
import { SCREENS, type ScreenId } from '../types'

// A 4-screen internal tool with no deep-linking requirement in docs/sip-ui-spec.md — plain state
// avoids a router dependency for something this small. `report` is the one run moving through
// the four screens in this session; it is lifted here (rather than fetched independently by each
// screen) because later screens' availability depends on this same report's state
// (schemas/state-machine.md — e.g. the CEO decision screen isn't reachable until QA has passed).
export function AppShell() {
  const [screen, setScreen] = useState<ScreenId>('brief-builder')
  const [report, setReport] = useState<DailyBriefReport>(() => newDraftReportFixture())

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-4xl px-4 py-4 sm:py-6">
          <h1 className="font-[family-name:var(--font-heading)] text-xl font-bold uppercase text-inzbc-navy sm:text-2xl">
            INZBC SIP Review
          </h1>
          <p className="mt-1 font-[family-name:var(--font-body)] text-sm text-slate-600">
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
                  className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium ${
                    screen === option.id
                      ? 'border-inzbc-tangerine text-inzbc-navy'
                      : 'border-transparent text-slate-500 hover:text-inzbc-navy'
                  }`}
                >
                  {option.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-6">
        {screen === 'brief-builder' ? <BriefBuilderScreen report={report} onChange={setReport} /> : null}
        {screen === 'qa-review' ? <QaReviewScreen report={report} onChange={setReport} /> : null}
        {screen === 'ceo-decision' ? <CeoDecisionScreen /> : null}
        {screen === 'distribution-status' ? <DistributionStatusScreen /> : null}
      </main>
    </div>
  )
}
