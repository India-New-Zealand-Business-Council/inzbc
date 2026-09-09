import { useEffect, useState } from 'react'
import type { DailyBriefReport, RunState } from '../domain'
import { newDraftReportFixture } from '../lib/fixtures'
import { listRuns, type RunOut } from '../api/runsClient'
import { BriefBuilderScreen } from '../screens/BriefBuilderScreen'
import { CeoDecisionScreen } from '../screens/CeoDecisionScreen'
import { DistributionStatusScreen } from '../screens/DistributionStatusScreen'
import { QaReviewScreen } from '../screens/QaReviewScreen'
import { RunsCandidatesScreen } from '../screens/RunsCandidatesScreen'
import { PlatformOverviewScreen } from '../screens/PlatformOverviewScreen'
import { SCREEN_GROUPS, type ScreenId } from '../types'
import { CommsAssistant } from '@comms/components/CommsAssistant'
import { FtaQuery } from '@fta/components/FtaQuery'
import { Dashboard as MemberDashboard } from '@member/pages/Dashboard'
import { Footer } from './Footer'

const LOGO_URL = 'https://static.wixstatic.com/media/df219d_0b8e6333d53841efaf66f675038a0798~mv2.jpg'

// Each screen says what it is and, where it matters, what it is honest about. The blurbs carry
// the caveats rather than the screens implying more than they do: a fixture-backed screen says
// so, and the Explainer says it makes no model call, because that is its whole design.
const HEADINGS: Record<ScreenId, { title: string; blurb: string }> = {
  overview: {
    title: 'INZBC Platform',
    blurb:
      'Four modules on one governed backend: trade intelligence, FTA guidance, communications drafting and member services.',
  },
  'runs-candidates': {
    title: 'Runs & Candidates',
    blurb:
      'Live from the database. Every candidate carries who captured it, who assessed it and who verified it, and the same person cannot do two of those.',
  },
  'brief-builder': {
    title: 'Brief Builder',
    blurb:
      'Assemble the daily brief against the SIP-185 mandatory source register. A source with no recorded outcome is a Critical stop at QA, not a warning.',
  },
  'qa-review': {
    title: 'QA Review',
    blurb:
      'The SIP-188 checklist, worked item by item. The reviewer cannot be the run’s analyst, and any Critical failure blocks release.',
  },
  'ceo-decision': {
    title: 'CEO Decision',
    blurb:
      'Ruling, approval and distribution authority are three separate recorded acts. Approving a report never causes anything to be sent.',
  },
  'distribution-status': {
    title: 'Distribution',
    blurb:
      'Distribution stays disabled by default and opens only on a recorded authority naming its recipient.',
  },
  fta: {
    title: 'FTA Explainer',
    blurb:
      'Answers from a curated, citation-carrying corpus and makes no model call at all, so it cannot invent a trade fact. No match returns a route to INZBC rather than a guess.',
  },
  comms: {
    title: 'Comms Assistant',
    blurb:
      'Drafts only. Nothing here publishes, a named reviewer approves every draft, and the author of a draft may not approve it.',
  },
  member: {
    title: 'Member Portal',
    blurb:
      'The member-facing surface. Interface shell against the live design system; membership itself remains in Member Jungle rather than duplicated here.',
  },
}

// A run in one of these has finished; nothing on the four workflow screens can act on it. Used
// only to pick a sensible run to open on -- every run stays selectable from Runs & Candidates,
// because looking at a closed run's record is a normal thing to want.
// The screens that act on one particular run, as opposed to the whole instance.
const WORKFLOW_SCREENS: ReadonlySet<ScreenId> = new Set<ScreenId>([
  'brief-builder',
  'qa-review',
  'ceo-decision',
  'distribution-status',
])

const TERMINAL: ReadonlySet<string> = new Set(['Distributed', 'Stopped', 'Closed', 'Withdrawn'])

/** A day, from the run's coverage window, in the `YYYY-MM-DD` form the brief header uses. */
function isoDay(utc: string): string {
  return utc.slice(0, 10)
}

/**
 * The brief for a real run: the SIP-050 section skeleton, carrying that run's identity and state.
 *
 * The sections stay empty. They are the template from the specification, and a run whose brief has
 * not been written has nothing in them -- inventing content here is exactly what the fixture id
 * this replaces was doing wrong. What changes is that the run number, state and coverage window
 * are now the ones in the database, so the workflow screens gate on the run's real state.
 */
function briefForRun(run: RunOut): DailyBriefReport {
  return {
    ...newDraftReportFixture(),
    runId: run.run_number,
    runVersion: run.version,
    state: run.state as RunState,
    reportDate: isoDay(run.coverage_end_utc),
    coverageStart: isoDay(run.coverage_start_utc),
    coverageEnd: isoDay(run.coverage_end_utc),
  }
}

// A 4-screen internal tool with no deep-linking requirement in docs/sip-ui-spec.md — plain state
// avoids a router dependency for something this small. `report` is the one run moving through
// the four screens in this session; it is lifted here (rather than fetched independently by each
// screen) because later screens' availability depends on this same report's state
// (schemas/state-machine.md — e.g. the CEO decision screen isn't reachable until QA has passed).
export function AppShell() {
  const [screen, setScreen] = useState<ScreenId>('overview')
  const [workingRun, setWorkingRun] = useState<RunOut | null>(null)
  // Edits are held against the run they were made on. The brief itself is derived below rather
  // than copied into state and kept in step with an effect: two sources for one value is how they
  // drift, and switching runs then has to remember to clear the stale one.
  const [edited, setEdited] = useState<{ runId: string; brief: DailyBriefReport } | null>(null)

  // Open on a real run rather than an invented one. The newest run that has not finished is the
  // one someone arriving at this tool is most likely working on; if every run has finished, the
  // newest of those is still a truer thing to show than a run number that exists nowhere.
  // A failure here leaves the empty draft in place, which is what the screens already handle.
  useEffect(() => {
    const controller = new AbortController()
    listRuns({ signal: controller.signal })
      .then((runs) => {
        const opening = runs.find((run) => !TERMINAL.has(run.state)) ?? runs[0]
        if (opening) setWorkingRun(opening)
      })
      .catch(() => {})
    return () => controller.abort()
  }, [])

  // Switching runs drops the previous run's edits by construction: they are keyed to a run id that
  // no longer matches, so no clearing step exists to forget. Carrying them across would attribute
  // one run's work to another.
  const report =
    edited && edited.runId === (workingRun?.id ?? '')
      ? edited.brief
      : workingRun
        ? briefForRun(workingRun)
        : newDraftReportFixture()

  const setReport = (next: DailyBriefReport) =>
    setEdited({ runId: workingRun?.id ?? '', brief: next })

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
            <span className="hidden text-sm font-medium text-inzbc-ink sm:inline">Platform</span>
          </div>
          <nav aria-label="Modules" className="overflow-x-auto">
            <ul className="flex items-center gap-1">
              {SCREEN_GROUPS.map((group, groupIndex) => (
                <li key={group.label} className="flex items-center gap-1">
                  {groupIndex > 0 ? (
                    <span aria-hidden="true" className="mx-1 h-4 w-px shrink-0 bg-inzbc-ink/15" />
                  ) : null}
                  {/* The group name is the accessible label for its own list rather than a
                      visible heading: nine tabs in one strip needs the grouping announced, and
                      there is no room in the pill for three more headings. */}
                  <ul aria-label={group.label} className="flex gap-1">
                    {group.screens.map((option) => (
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
          <h1 className="text-2xl font-extrabold text-inzbc-navy sm:text-3xl">{HEADINGS[screen].title}</h1>
          <p className="mt-2 max-w-3xl text-slate-700">{HEADINGS[screen].blurb}</p>
          {/* Which run the workflow screens are acting on. Named on every one of them, because a
              screen that gates on a run's state should say which run it means. */}
          {WORKFLOW_SCREENS.has(screen) ? (
            <p className="mt-2 text-sm text-slate-600">
              {workingRun ? (
                <>
                  Working run <strong className="text-inzbc-navy">{workingRun.run_number}</strong> ·{' '}
                  {workingRun.state} — change it under Runs &amp; Candidates.
                </>
              ) : (
                <>No run selected yet — choose one under Runs &amp; Candidates.</>
              )}
            </p>
          ) : null}
        </div>
        {screen === 'brief-builder' ? <BriefBuilderScreen report={report} onChange={setReport} /> : null}
        {screen === 'qa-review' ? <QaReviewScreen report={report} onChange={setReport} /> : null}
        {screen === 'ceo-decision' ? <CeoDecisionScreen report={report} onChange={setReport} /> : null}
        {screen === 'distribution-status' ? <DistributionStatusScreen report={report} /> : null}
        {screen === 'runs-candidates' ? (
          <RunsCandidatesScreen onWorkRun={setWorkingRun} workingRunId={workingRun?.id ?? null} />
        ) : null}
        {screen === 'overview' ? <PlatformOverviewScreen /> : null}
        {screen === 'fta' ? <FtaQuery /> : null}
        {screen === 'comms' ? <CommsAssistant /> : null}
        {screen === 'member' ? <MemberDashboard /> : null}
      </main>
      <Footer />
    </div>
  )
}
