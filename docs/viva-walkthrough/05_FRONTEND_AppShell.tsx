// ==============================================================================
// FILE 5 OF 5: FRONTEND UNIFIED SHELL (from apps/sip/ui/src/components/AppShell.tsx)
// HOW IT WORKS:
//   - React 18 + TypeScript + Vite + Tailwind CSS (WCAG 2.2 AA accessible).
//   - Unites all 4 INZBC modules in one governed shell:
//       1) SIP Daily Workflow (Runs, Brief Builder, QA Review, CEO Decision, Distribution)
//       2) FTA Explainer (zero-LLM citation-carrying tariff Q&A + explicit No Match)
//       3) Comms Assistant (SSE streaming drafts behind named-reviewer gate)
//       4) Member Portal (authoritative Member Jungle link-out)
//   - Hydrates live state from FastAPI (`listRuns`) — never fabricates placeholder data.
// ==============================================================================

import { useEffect, useState } from 'react'                        // React state & lifecycle hooks
import type { DailyBriefReport, RunState } from '../domain'        // Shared TypeScript domain types
import { newDraftReportFixture } from '../lib/fixtures'            // Empty SIP-050 section skeleton
import { listRuns, type RunOut } from '../api/runsClient'          // Typed HTTP client calling FastAPI /api/runs

// --- SIP Workflow Screens (each enforces one stage of the state machine) ---
import { BriefBuilderScreen } from '../screens/BriefBuilderScreen'           // Assemble brief + 112-source checklist
import { CeoDecisionScreen } from '../screens/CeoDecisionScreen'             // Separate CEO ruling, approval & authority
import { DistributionStatusScreen } from '../screens/DistributionStatusScreen' // Fail-closed distribution release gate
import { QaReviewScreen } from '../screens/QaReviewScreen'                   // Independent QA checklist (SoD enforced)
import { RunsCandidatesScreen } from '../screens/RunsCandidatesScreen'       // Live DB runs + candidate SoD verification
import { PlatformOverviewScreen } from '../screens/PlatformOverviewScreen'   // Live platform scale & module launcher
import { GettingStartedScreen } from '../screens/GettingStartedScreen'       // Role & governance onboarding screen

// --- Other 3 Platform Modules Mounted Inside the Same Governed Shell ---
import { CommsAssistant } from '@comms/components/CommsAssistant'  // SSE Comms drafting + deletion-reason modal
import { FtaQuery } from '@fta/components/FtaQuery'                // Grounded FTA tariff lookup (zero LLM calls)
import { Dashboard as MemberDashboard } from '@member/pages/Dashboard' // Member portal linking to Member Jungle

// --- Explicit Governance Headings & Honesty Blurbs for Every Screen ---
const HEADINGS = {
  overview: {
    title: 'INZBC Platform',
    blurb: 'Four modules on one governed backend: trade intelligence, FTA guidance, communications drafting and member services.',
  },
  'runs-candidates': {
    title: 'Runs & Candidates',
    // Server enforces Segregation of Duties (HTTP 403) if same actor tries to self-verify
    blurb: 'Live from the database. Every candidate carries who captured it, who assessed it and who verified it, and the same person cannot do two of those.',
  },
  'brief-builder': {
    title: 'Brief Builder',
    // Missing source check outcome blocks QA automatically
    blurb: 'Assemble the daily brief against the SIP-185 mandatory source register. A source with no recorded outcome is a Critical stop at QA.',
  },
  'qa-review': {
    title: 'QA Review',
    // Enforces productive friction: untouched pending sections cannot be rubber-stamped (PR #553)
    blurb: 'The SIP-188 checklist, worked item by item. The reviewer cannot be the run’s analyst, and any Critical failure blocks release.',
  },
  'ceo-decision': {
    title: 'CEO Decision',
    // Approving a report NEVER auto-sends anything
    blurb: 'Ruling, approval and distribution authority are three separate recorded acts. Approving a report never causes anything to be sent.',
  },
  'distribution-status': {
    title: 'Distribution',
    // Fail-closed button disabled until all 4 prerequisite DB records exist
    blurb: 'Distribution stays disabled by default and opens only on a recorded authority naming its recipient.',
  },
  fta: {
    title: 'FTA Explainer',
    // Deterministic lexical/BM25 retrieval only — zero LLM hallucination risk
    blurb: 'Answers from a curated, citation-carrying corpus and makes no model call at all. No match returns a route to INZBC rather than a guess.',
  },
  comms: {
    title: 'Comms Assistant',
    blurb: 'Drafts only. Nothing here publishes, a named reviewer approves every draft, and the author of a draft may not approve it.',
  },
  member: {
    title: 'Member Portal',
    blurb: 'Member-facing surface; authoritative membership records stay in Member Jungle rather than being duplicated.',
  },
}

// --- Workflow vs. Terminal State Guards ---
// Only these 4 screens operate on a single active SIP run:
const WORKFLOW_SCREENS = new Set(['brief-builder', 'qa-review', 'ceo-decision', 'distribution-status'])

// Runs in these states are finished; UI locks out mutations (matches orchestrator.py terminal sets):
const TERMINAL = new Set(['Distributed', 'Stopped', 'Closed', 'Withdrawn'])

// Format UTC timestamp -> YYYY-MM-DD for brief header display
function isoDay(utc: string): string {
  return utc.slice(0, 10)
}

// --- Hydrate Real Database Run Into the SIP-050 Brief Skeleton ---
// Keeps sections empty until written (no fake placeholder content), binding the UI
// directly to the run's live PostgreSQL `state`, `id`, and 24-hour coverage window.
function briefForRun(run: RunOut): DailyBriefReport {
  return {
    ...newDraftReportFixture(),          // Empty SIP-050 structural template
    runId: run.id,                       // Real Postgres UUID
    runNumber: run.run_number,           // Sequential run number
    runVersion: run.version,             // Optimistic concurrency version
    state: run.state as RunState,        // Real DB state -> gates QA/CEO/Distribution buttons
    reportDate: isoDay(run.coverage_end_utc),
    coverageStart: isoDay(run.coverage_start_utc),
    coverageEnd: isoDay(run.coverage_end_utc),
  }
}
