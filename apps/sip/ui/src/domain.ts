/**
 * Domain types for the SIP review/approval UI, mirrored from docs/sip-ui-spec.md,
 * docs/sip/launch/SIP-186_daily_brief_template_v0.9.md,
 * docs/sip/launch/SIP-188_qa_checklist_v0.9.md and schemas/state-machine.md.
 *
 * `POST /api/reports`, `POST /api/reports/{id}/qa`, `GET /api/reports/{id}` and
 * `POST /api/runs/{id}/fail-qa` are live now (#124, #285) — see api/reportsStore.ts, which calls
 * them. The report-decision endpoints (`/approval`, `/ruling`, `/distribution`) are still not
 * mounted; `decision_role_permissions` is unseeded, which is a client decision pending (ADR-0005
 * follow-up 4), not an engineering gap — reportsStore.ts's `recordCeoDecision` and
 * `authoriseDistribution` document that and stay fixture-backed until it lands.
 */

// schemas/state-machine.md's state list. 'Continue' and 'Continue With Correction' are included
// as states, not just decision labels: the state machine lists
// "Awaiting CEO Decision -> Continue / Continue With Correction / Paused / Stopped" as transition
// targets distinct from "Awaiting CEO Decision -> Approved for Manual Distribution" (which only
// happens when distribution is separately authorised) — see lib/stateMachine.ts.
export type RunState =
  | 'Draft'
  | 'Run Authorised'
  | 'Coverage Locked'
  | 'Scanning'
  | 'Candidate Review'
  | 'Report Drafted'
  | 'QA In Progress'
  | 'QA Failed'
  | 'Awaiting CEO Decision'
  | 'Continue'
  | 'Continue With Correction'
  | 'Approved for Manual Distribution'
  | 'Distributed'
  | 'Closed'
  | 'Paused'
  | 'Stopped'

export type SignalStrength = 'Critical' | 'High' | 'Medium' | 'Low'
export type VerificationStatus = 'Verified' | 'Unverified' | 'Pending'

/** GET /api/candidates?run=:id — a scored candidate the analyst can select into the brief. */
export interface Candidate {
  id: string
  headline: string
  sourceName: string
  sip185Code: string
  sector: string
  signalStrength: SignalStrength
  sourceConfidence: string
  verificationStatus: VerificationStatus
}

/** SIP-186 §3 — Critical and High signals (ranked). */
export interface CriticalHighSignal {
  id: string
  headline: string
  whatHappened: string
  whyItMatters: string
  memberImpact: string
  signalStrength: SignalStrength
  sourceConfidence: string
  verificationStatus: VerificationStatus
  recommendedCeoAction: string
  recommendedMemberAction: string
  primarySourceUrl: string
  registerRouting: string
  nextTriggerDate: string
}

/** SIP-186 §7 — CEO action list (repeatable rows). */
export interface CeoActionItem {
  id: string
  action: string
  owner: string
  priority: 'High' | 'Medium' | 'Low'
  dueDate: string
  evidenceRequirement: string
}

// SIP-185's canonical outcome codes (docs/sip/launch/SIP-185_source_register_v0.9.md), also
// mirrored in docs/sip/SIP_Reference_Config.json's `source_outcomes` — the list SIP-188 checks
// for blanks against every applicable mandatory source. '' = not yet recorded (the blank state
// that blocks submission for an applicable mandatory source, per the brief builder's rule).
export type SourceOutcome =
  | 'Included'
  | 'Context'
  | 'Suppressed'
  | 'Inaccessible'
  | 'Excluded'
  | 'No Qualifying Item'
  | ''

/** SIP-186 §12 — mandatory sources scanned + outcome each. */
export interface SourceCoverageRow {
  sourceId: string
  sourceName: string
  sip185Code: string
  mandatory: boolean
  outcome: SourceOutcome
  fallbackAttempt: string
}

export type ReviewStatus = 'pending' | 'approved' | 'flagged'

/** One free-text SIP-186 section (§§1, 2, 4-6, 8-10) — editable and reviewable in QA. */
export interface BriefSection {
  id: string
  title: string
  content: string
  reviewStatus: ReviewStatus
  flagReason: string
}

export const REVIEWABLE_SECTION_TITLES = [
  '1. Executive judgement',
  '2. Executive summary',
  '4. Key bilateral developments',
  '5. Opportunities',
  '6. Threats and risks',
  '8. Member actions',
  '9. Watch-list updates',
  '10. Active Carry-Forward',
] as const

/** SIP-188 tri-state checklist item — a plain checkbox in the source doc, tri-state per the UI spec. */
export type QaAnswer = 'pass' | 'fail' | 'na'

export interface QaChecklistItem {
  id: string
  text: string
  critical: boolean
  answer: QaAnswer | null
}

export interface QaChecklistGroup {
  id: string
  title: string
  items: QaChecklistItem[]
}

export interface QaResult {
  reviewer: string
  timestamp: string
  result: 'Pass' | 'Fail' | null
  criticalFailuresFound: string
  correctionsRequired: string
}

export type ReportDecisionType = 'continue' | 'continue_with_correction' | 'pause' | 'stop'

export interface CeoDecisionRecord {
  reportVersion: string
  decision: ReportDecisionType | null
  reason: string
  conditions: string
  owner: string
  evidenceReference: string
  nextReviewDate: string
  decidedAt: string | null
  // Deliberately independent of `decision` above — docs/sip-ui-spec.md Screen 3: "The UI must not
  // let the CEO set this in the same submit as decision 1 ... Approval alone is not permission to
  // send." `null` = not yet decided; `false` is a complete, valid outcome, not an error state.
  distributionAuthorised: boolean | null
  distributionDecidedAt: string | null
}

export interface DistributionRecord {
  sent: boolean
  sender: string
  recipient: string
  sendTime: string
  channel: string
  deliveryResult: string
  closeOutStatus: string
}

export interface DailyBriefReport {
  id: string
  runId: string
  // Optimistic-concurrency version of `runId`'s row in `runs` (`services/api/runs.py`'s
  // `TransitionIn.expected_version`) — a fixture never needed this, since nothing else could race
  // an in-memory object. A real lifecycle transition (fail-qa, and eventually the others) has to
  // pass back the version it read, or the server refuses it as stale rather than silently
  // clobbering a concurrent change. Starts at 0, matching a freshly created run.
  runVersion: number
  // The report_version row `POST /api/reports` created for this brief, once it exists —
  // `services/api/reports.py`'s `ReportVersionOut.id`. `null` until submitted. Needed by
  // `POST /api/reports/{id}/qa`, which records a result against a specific version, not against
  // the run.
  reportVersionId: string | null
  reportDate: string
  coverageStart: string
  coverageEnd: string
  generatedAt: string
  analyst: string
  reviewer: string
  // The daily report's own version — bumped by reportsStore.submitReportForQa each time a
  // corrected brief is resubmitted after a QA Failed round. Distinct from `approvedVersionSet`
  // (the controlling document list this report was built against, e.g. "SIP-050 v1.1, DB v1.9,
  // ...") — an earlier version of CeoDecisionScreen populated CeoDecisionRecord.reportVersion
  // from approvedVersionSet, so the recorded decision named the wrong document as its subject.
  reportVersion: string
  approvedVersionSet: string
  sourceConfidenceSummary: string
  sourceMix: string
  state: RunState
  focusNote: string
  // Ids into candidatesFixture(), not the candidates themselves — mirrors how a real API would
  // take selected ids and resolve them server-side, and means selection survives navigating
  // between screens (this is part of the lifted `report` state in AppShell, not component state
  // that unmounts). An earlier version kept this as local state in BriefBuilderScreen and passed
  // only a *count* to submitReportForQa, so the actual selected candidates never reached the
  // generated digest — see generatedDigestContent's docstring in lib/fixtures.ts.
  selectedCandidateIds: string[]
  sections: BriefSection[]
  criticalHighSignals: CriticalHighSignal[]
  ceoActionList: CeoActionItem[]
  sourceCoverage: SourceCoverageRow[]
  noMaterialNewSignal: boolean
  qaChecklist: QaChecklistGroup[]
  qa: QaResult | null
  decision: CeoDecisionRecord | null
  distribution: DistributionRecord | null
}

export const GOVERNANCE_LINE =
  'Human-reviewed. Not authorised for member, external, website or social publication.'
