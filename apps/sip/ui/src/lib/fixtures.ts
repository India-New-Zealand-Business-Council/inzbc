/**
 * Contract fixtures for local development and tests — not real INZBC intelligence output.
 *
 * MANDATORY_SOURCES below is generated from the real SIP-185 mandatory source register
 * (`apps/sip/collector/data/sip185_sources_v1.0.csv`) — all 112 rows where `mandatory=true`, ids
 * and codes copied verbatim as `source_id`. An earlier version of this fixture invented its own
 * 8-row list with codes like `OFF-NZ-MFAT` that matched nothing in the real register, so the
 * blank-mandatory-source check in `lib/validation.ts` (and SIP-188 checklist item b2) could only
 * ever see 8 of the 112 sources that actually gate submission. Regenerate this block if the CSV
 * changes: `node <(node -e "...")` isn't checked in, but the mapping is source_id -> {id:
 * source_id, sip185Code: source_id, name}, filtered to mandatory=true.
 *
 * Every headline, judgement and signal elsewhere in this file is invented placeholder text for UI
 * development, per PROJECT-RULES.md's "never invent statistics, member counts, board names, or FTA
 * details" — each is prefixed `[FIXTURE]` so it can never be mistaken for real output if this
 * ever renders somewhere unexpected.
 */

import type { Candidate, DailyBriefReport, QaChecklistGroup, SourceCoverageRow } from '../domain'

// Generated from apps/sip/collector/data/sip185_sources_v1.0.csv — 112 mandatory rows.
export const MANDATORY_SOURCES: { id: string; sip185Code: string; name: string }[] = [
  { id: 'NZ-OFF-001', sip185Code: 'NZ-OFF-001', name: 'New Zealand Parliament' },
  { id: 'NZ-OFF-002', sip185Code: 'NZ-OFF-002', name: 'New Zealand Select Committees' },
  { id: 'NZ-OFF-003', sip185Code: 'NZ-OFF-003', name: 'New Zealand Legislation' },
  { id: 'NZ-OFF-004', sip185Code: 'NZ-OFF-004', name: 'New Zealand Gazette' },
  { id: 'NZ-OFF-005', sip185Code: 'NZ-OFF-005', name: 'Beehive' },
  { id: 'NZ-OFF-006', sip185Code: 'NZ-OFF-006', name: 'Ministry of Foreign Affairs and Trade' },
  { id: 'NZ-OFF-007', sip185Code: 'NZ-OFF-007', name: 'New Zealand Trade and Enterprise' },
  { id: 'NZ-OFF-008', sip185Code: 'NZ-OFF-008', name: 'Ministry of Business, Innovation and Employment' },
  { id: 'NZ-OFF-009', sip185Code: 'NZ-OFF-009', name: 'Ministry for Primary Industries' },
  { id: 'NZ-OFF-010', sip185Code: 'NZ-OFF-010', name: 'New Zealand Customs Service' },
  { id: 'NZ-OFF-011', sip185Code: 'NZ-OFF-011', name: 'Immigration New Zealand' },
  { id: 'NZ-OFF-012', sip185Code: 'NZ-OFF-012', name: 'Education New Zealand' },
  { id: 'NZ-OFF-013', sip185Code: 'NZ-OFF-013', name: 'Stats NZ' },
  { id: 'NZ-OFF-014', sip185Code: 'NZ-OFF-014', name: 'Reserve Bank of New Zealand' },
  { id: 'NZ-OFF-015', sip185Code: 'NZ-OFF-015', name: 'Commerce Commission' },
  { id: 'NZ-OFF-016', sip185Code: 'NZ-OFF-016', name: 'New Zealand Treasury' },
  { id: 'NZ-OFF-017', sip185Code: 'NZ-OFF-017', name: 'Inland Revenue' },
  { id: 'NZ-OFF-018', sip185Code: 'NZ-OFF-018', name: 'Ministry for Cities, Environment, Regions and Transport' },
  { id: 'NZ-OFF-020', sip185Code: 'NZ-OFF-020', name: 'Civil Aviation Authority and Aviation Security Service' },
  { id: 'NZ-OFF-021', sip185Code: 'NZ-OFF-021', name: 'Maritime New Zealand' },
  { id: 'NZ-OFF-022', sip185Code: 'NZ-OFF-022', name: 'Ministry for the Environment' },
  { id: 'NZ-OFF-025', sip185Code: 'NZ-OFF-025', name: 'Financial Markets Authority' },
  { id: 'NZ-OFF-027', sip185Code: 'NZ-OFF-027', name: 'Overseas Investment Office' },
  { id: 'NZ-OFF-028', sip185Code: 'NZ-OFF-028', name: 'Ministry of Defence' },
  { id: 'NZ-OFF-030', sip185Code: 'NZ-OFF-030', name: 'Ministry of Education' },
  { id: 'NZ-OFF-033', sip185Code: 'NZ-OFF-033', name: 'Tourism New Zealand' },
  { id: 'NZ-OFF-035', sip185Code: 'NZ-OFF-035', name: 'Ministry for Regulation' },
  { id: 'IND-OFF-001', sip185Code: 'IND-OFF-001', name: 'Press Information Bureau' },
  { id: 'IND-OFF-002', sip185Code: 'IND-OFF-002', name: 'Department of Commerce' },
  { id: 'IND-OFF-003', sip185Code: 'IND-OFF-003', name: 'Directorate General of Foreign Trade' },
  { id: 'IND-OFF-004', sip185Code: 'IND-OFF-004', name: 'Directorate General of Trade Remedies' },
  { id: 'IND-OFF-005', sip185Code: 'IND-OFF-005', name: 'Ministry of External Affairs' },
  { id: 'IND-OFF-006', sip185Code: 'IND-OFF-006', name: 'Reserve Bank of India' },
  { id: 'IND-OFF-007', sip185Code: 'IND-OFF-007', name: 'Ministry of Finance' },
  { id: 'IND-OFF-008', sip185Code: 'IND-OFF-008', name: 'Department of Economic Affairs' },
  { id: 'IND-OFF-009', sip185Code: 'IND-OFF-009', name: 'Department of Revenue' },
  { id: 'IND-OFF-010', sip185Code: 'IND-OFF-010', name: 'Central Board of Indirect Taxes and Customs' },
  { id: 'IND-OFF-011', sip185Code: 'IND-OFF-011', name: 'ICEGATE' },
  { id: 'IND-OFF-012', sip185Code: 'IND-OFF-012', name: 'GST Council' },
  { id: 'IND-OFF-013', sip185Code: 'IND-OFF-013', name: 'Ministry of Textiles' },
  { id: 'IND-OFF-014', sip185Code: 'IND-OFF-014', name: 'Department of Agriculture and Farmers Welfare' },
  {
    id: 'IND-OFF-015',
    sip185Code: 'IND-OFF-015',
    name: 'Agricultural and Processed Food Products Export Development Authority',
  },
  { id: 'IND-OFF-016', sip185Code: 'IND-OFF-016', name: 'Food Safety and Standards Authority of India' },
  { id: 'IND-OFF-018', sip185Code: 'IND-OFF-018', name: 'Ministry of Electronics and Information Technology' },
  {
    id: 'IND-OFF-019',
    sip185Code: 'IND-OFF-019',
    name: 'Department for Promotion of Industry and Internal Trade',
  },
  { id: 'IND-OFF-020', sip185Code: 'IND-OFF-020', name: 'Invest India' },
  { id: 'IND-OFF-022', sip185Code: 'IND-OFF-022', name: 'Ministry of Corporate Affairs' },
  { id: 'IND-OFF-023', sip185Code: 'IND-OFF-023', name: 'Securities and Exchange Board of India' },
  { id: 'IND-OFF-026', sip185Code: 'IND-OFF-026', name: 'Ministry of Education' },
  { id: 'IND-OFF-028', sip185Code: 'IND-OFF-028', name: 'Ministry of Tourism' },
  { id: 'IND-OFF-029', sip185Code: 'IND-OFF-029', name: 'Ministry of Civil Aviation' },
  { id: 'IND-OFF-032', sip185Code: 'IND-OFF-032', name: 'Ministry of Ports, Shipping and Waterways' },
  { id: 'IND-OFF-034', sip185Code: 'IND-OFF-034', name: 'Ministry of Defence' },
  { id: 'IND-OFF-036', sip185Code: 'IND-OFF-036', name: 'Ministry of New and Renewable Energy' },
  { id: 'IND-OFF-039', sip185Code: 'IND-OFF-039', name: 'NITI Aayog' },
  { id: 'IND-OFF-040', sip185Code: 'IND-OFF-040', name: 'Ministry of Statistics and Programme Implementation' },
  { id: 'IND-OFF-041', sip185Code: 'IND-OFF-041', name: 'Bureau of Indian Standards' },
  { id: 'IND-OFF-043', sip185Code: 'IND-OFF-043', name: 'Ministry of Labour and Employment' },
  { id: 'INT-001', sip185Code: 'INT-001', name: 'World Trade Organization' },
  { id: 'INT-002', sip185Code: 'INT-002', name: 'World Bank' },
  { id: 'INT-003', sip185Code: 'INT-003', name: 'International Monetary Fund' },
  { id: 'INT-004', sip185Code: 'INT-004', name: 'Organisation for Economic Co-operation and Development' },
  { id: 'INT-014', sip185Code: 'INT-014', name: 'International Labour Organization' },
  { id: 'NZ-SEC-002', sip185Code: 'NZ-SEC-002', name: 'ExportNZ' },
  { id: 'NZ-SEC-004', sip185Code: 'NZ-SEC-004', name: 'DairyNZ' },
  { id: 'NZ-SEC-005', sip185Code: 'NZ-SEC-005', name: 'Dairy Companies Association of New Zealand' },
  { id: 'NZ-SEC-007', sip185Code: 'NZ-SEC-007', name: 'Beef + Lamb New Zealand' },
  { id: 'NZ-SEC-008', sip185Code: 'NZ-SEC-008', name: 'Meat Industry Association' },
  { id: 'NZ-SEC-009', sip185Code: 'NZ-SEC-009', name: 'Horticulture New Zealand' },
  { id: 'NZ-SEC-010', sip185Code: 'NZ-SEC-010', name: 'New Zealand Apples and Pears' },
  { id: 'NZ-SEC-011', sip185Code: 'NZ-SEC-011', name: 'Zespri' },
  { id: 'NZ-SEC-012', sip185Code: 'NZ-SEC-012', name: 'Apiculture New Zealand' },
  { id: 'NZ-SEC-014', sip185Code: 'NZ-SEC-014', name: 'Seafood New Zealand' },
  { id: 'NZ-SEC-016', sip185Code: 'NZ-SEC-016', name: 'New Zealand Winegrowers' },
  { id: 'NZ-SEC-017', sip185Code: 'NZ-SEC-017', name: 'New Zealand Forest Owners Association' },
  { id: 'NZ-SEC-019', sip185Code: 'NZ-SEC-019', name: 'Wool Impact' },
  { id: 'NZ-SEC-021', sip185Code: 'NZ-SEC-021', name: 'Universities New Zealand' },
  { id: 'NZ-SEC-022', sip185Code: 'NZ-SEC-022', name: 'Tourism Industry Aotearoa' },
  { id: 'NZ-SEC-023', sip185Code: 'NZ-SEC-023', name: 'Air New Zealand Newsroom' },
  { id: 'NZ-SEC-024', sip185Code: 'NZ-SEC-024', name: 'NZTech' },
  { id: 'NZ-SEC-025', sip185Code: 'NZ-SEC-025', name: 'Payments New Zealand' },
  { id: 'NZ-SEC-026', sip185Code: 'NZ-SEC-026', name: 'India New Zealand Business Council' },
  { id: 'IND-SEC-001', sip185Code: 'IND-SEC-001', name: 'Federation of Indian Export Organisations' },
  { id: 'IND-SEC-002', sip185Code: 'IND-SEC-002', name: 'Confederation of Indian Industry' },
  {
    id: 'IND-SEC-003',
    sip185Code: 'IND-SEC-003',
    name: 'Federation of Indian Chambers of Commerce and Industry',
  },
  { id: 'IND-SEC-005', sip185Code: 'IND-SEC-005', name: 'NASSCOM' },
  { id: 'IND-SEC-006', sip185Code: 'IND-SEC-006', name: 'Engineering Export Promotion Council India' },
  { id: 'IND-SEC-007', sip185Code: 'IND-SEC-007', name: 'Services Export Promotion Council' },
  { id: 'IND-SEC-008', sip185Code: 'IND-SEC-008', name: 'Confederation of Indian Textile Industry' },
  { id: 'IND-SEC-009', sip185Code: 'IND-SEC-009', name: 'Bharat Tex' },
  { id: 'IND-SEC-012', sip185Code: 'IND-SEC-012', name: 'National Payments Corporation of India' },
  { id: 'NZ-MED-001', sip185Code: 'NZ-MED-001', name: 'New Zealand Herald' },
  { id: 'NZ-MED-002', sip185Code: 'NZ-MED-002', name: 'RNZ' },
  { id: 'NZ-MED-003', sip185Code: 'NZ-MED-003', name: '1News' },
  { id: 'NZ-MED-004', sip185Code: 'NZ-MED-004', name: 'Stuff' },
  { id: 'NZ-MED-005', sip185Code: 'NZ-MED-005', name: 'Newsroom' },
  { id: 'NZ-MED-006', sip185Code: 'NZ-MED-006', name: 'BusinessDesk' },
  { id: 'NZ-MED-007', sip185Code: 'NZ-MED-007', name: 'National Business Review' },
  { id: 'NZ-MED-008', sip185Code: 'NZ-MED-008', name: 'Newstalk ZB' },
  { id: 'NZ-MED-009', sip185Code: 'NZ-MED-009', name: 'interest.co.nz' },
  { id: 'NZ-MED-010', sip185Code: 'NZ-MED-010', name: 'Rural News Group' },
  { id: 'NZ-MED-011', sip185Code: 'NZ-MED-011', name: 'Farmers Weekly' },
  { id: 'NZ-MED-012', sip185Code: 'NZ-MED-012', name: 'Indian Newslink' },
  { id: 'NZ-MED-013', sip185Code: 'NZ-MED-013', name: 'Indian Weekender' },
  { id: 'NZ-MED-014', sip185Code: 'NZ-MED-014', name: 'Awaaz' },
  { id: 'IND-MED-001', sip185Code: 'IND-MED-001', name: 'The Economic Times' },
  { id: 'IND-MED-002', sip185Code: 'IND-MED-002', name: 'Business Standard' },
  { id: 'IND-MED-003', sip185Code: 'IND-MED-003', name: 'Financial Express' },
  { id: 'IND-MED-004', sip185Code: 'IND-MED-004', name: 'The Hindu BusinessLine' },
  { id: 'IND-MED-005', sip185Code: 'IND-MED-005', name: 'Mint' },
  { id: 'IND-MED-006', sip185Code: 'IND-MED-006', name: 'Moneycontrol' },
  { id: 'GLB-MED-001', sip185Code: 'GLB-MED-001', name: 'Reuters' },
]

export function sourceCoverageFixture(): SourceCoverageRow[] {
  return MANDATORY_SOURCES.map((source) => ({
    sourceId: source.id,
    sourceName: source.name,
    sip185Code: source.sip185Code,
    mandatory: true,
    outcome: '',
    fallbackAttempt: '',
  }))
}

export function candidatesFixture(): Candidate[] {
  return [
    {
      id: 'cand-1',
      headline: '[FIXTURE] Tariff schedule update noted for dairy exports',
      sourceName: 'Ministry of Foreign Affairs and Trade',
      sip185Code: 'NZ-OFF-006',
      sector: 'Dairy',
      signalStrength: 'High',
      sourceConfidence: 'Official',
      verificationStatus: 'Verified',
    },
    {
      id: 'cand-2',
      headline: '[FIXTURE] Ministerial statement on bilateral trade talks',
      sourceName: 'Beehive',
      sip185Code: 'NZ-OFF-005',
      sector: 'Bilateral',
      signalStrength: 'Critical',
      sourceConfidence: 'Official',
      verificationStatus: 'Verified',
    },
    {
      id: 'cand-3',
      headline: '[FIXTURE] Sector commentary on wool market conditions',
      sourceName: 'RNZ',
      sip185Code: 'NZ-MED-002',
      sector: 'Wool',
      signalStrength: 'Medium',
      sourceConfidence: 'Media',
      verificationStatus: 'Unverified',
    },
    {
      id: 'cand-4',
      headline: '[FIXTURE] DGFT notice referenced in import-compliance monitoring',
      sourceName: 'Directorate General of Foreign Trade',
      sip185Code: 'IND-OFF-003',
      sector: 'Compliance',
      signalStrength: 'High',
      sourceConfidence: 'Official',
      verificationStatus: 'Pending',
    },
  ]
}

/** SIP-188's five checklist groups, verbatim item text, Critical flags as marked in the source doc. */
export function qaChecklistFixture(): QaChecklistGroup[] {
  return [
    {
      id: 'authority-and-versions',
      title: 'Authority and versions',
      items: [
        {
          id: 'a1',
          text: 'Run authority active (SIP-191), date within run window, operator authorised.',
          critical: false,
          answer: null,
        },
        {
          id: 'a2',
          text: 'Approved version set present; no uncontrolled change.',
          critical: true,
          answer: null,
        },
      ],
    },
    {
      id: 'coverage-and-sources',
      title: 'Coverage and sources',
      items: [
        {
          id: 'b1',
          text: 'Coverage window is exactly 24h, Pacific/Auckland, timestamps recorded.',
          critical: false,
          answer: null,
        },
        {
          id: 'b2',
          text: 'Every applicable mandatory source has an outcome.',
          critical: true,
          answer: null,
        },
        {
          id: 'b3',
          text: 'Inaccessible sources show fallback attempts + reason; not silently omitted.',
          critical: false,
          answer: null,
        },
      ],
    },
    {
      id: 'content-quality',
      title: 'Content quality',
      items: [
        {
          id: 'c1',
          text: 'Freshness: publication vs event date checked; nothing old shown as new.',
          critical: false,
          answer: null,
        },
        {
          id: 'c2',
          text: 'Relevance: each item passes NZ + INZBC/member tests; no generic India news.',
          critical: false,
          answer: null,
        },
        {
          id: 'c3',
          text: 'Verification: every High/Critical claim has official/high-confidence evidence.',
          critical: true,
          answer: null,
        },
        {
          id: 'c4',
          text: 'No High/Critical claim rests on a snippet, inaccessible article, or single weak source.',
          critical: false,
          answer: null,
        },
        { id: 'c5', text: 'Duplicates merged to one canonical item.', critical: false, answer: null },
        {
          id: 'c6',
          text: 'Active Carry-Forward correctly labelled (not presented as new).',
          critical: false,
          answer: null,
        },
        {
          id: 'c7',
          text: 'No Material New Signal used honestly where applicable; no filler.',
          critical: false,
          answer: null,
        },
        { id: 'c8', text: 'Factual consistency; facts separated from analysis.', critical: false, answer: null },
      ],
    },
    {
      id: 'records-and-routing',
      title: 'Records and routing',
      items: [
        { id: 'd1', text: 'Report follows SIP-186 structure.', critical: false, answer: null },
        {
          id: 'd2',
          text: "Every action has an owner and due/review date; no orphaned actions.",
          critical: false,
          answer: null,
        },
        {
          id: 'd3',
          text: 'Register routing correct; DB is the single Action Register (not SIP-187).',
          critical: false,
          answer: null,
        },
        {
          id: 'd4',
          text: 'DB and tracker reconciled (IDs, owners, statuses, dates, routing, evidence).',
          critical: true,
          answer: null,
        },
        { id: 'd5', text: 'Evidence retained (append-only; no overwrite).', critical: false, answer: null },
      ],
    },
    {
      id: 'approval-and-distribution',
      title: 'Approval and distribution',
      items: [
        {
          id: 'e1',
          text: 'Human approval recorded before distribution.',
          critical: true,
          answer: null,
        },
        {
          id: 'e2',
          // Verbatim from docs/sip/launch/SIP-188_qa_checklist_v0.9.md:37 — an earlier version
          // softened the named recipient to "the authorised recipient on file", which drifts
          // from the source doc's actual checklist wording.
          text: 'Distribution authority correct; recipient limited to sunilkaushalnz@gmail.com.',
          critical: false,
          answer: null,
        },
        {
          id: 'e3',
          text: 'No automated/member/external/website/social distribution.',
          critical: false,
          answer: null,
        },
      ],
    },
  ]
}

/**
 * Stand-in for what the real pipeline (Roshan's side) would generate from the selected
 * candidates once a brief is submitted. Every value is invented placeholder text for UI
 * development — `[FIXTURE]`-prefixed so it can never be mistaken for a real digest — used so the
 * QA review screen has representative content to render, edit and score against.
 *
 * `criticalHighSignals` and `sourceMix` are derived from `selectedCandidates` — an earlier
 * version of this function ignored its caller entirely and always returned the same two
 * hardcoded signals (a ministerial statement and a tariff update), regardless of what the analyst
 * actually selected in BriefBuilderScreen. Selecting only a Medium/Unverified candidate produced
 * unrelated Critical/High signals in the QA review. Free-text sections (executive judgement,
 * summary, etc.) stay as generic placeholders — a real pipeline would write connected narrative
 * prose across candidates, which isn't something to fake a per-candidate mapping for here.
 */
export function generatedDigestContent(
  selectedCandidates: Candidate[],
): Pick<DailyBriefReport, 'sections' | 'criticalHighSignals' | 'ceoActionList' | 'sourceConfidenceSummary' | 'sourceMix'> {
  const criticalHighSignals = selectedCandidates
    .filter((candidate) => candidate.signalStrength === 'Critical' || candidate.signalStrength === 'High')
    .map((candidate, index) => ({
      id: `signal-${candidate.id}`,
      headline: candidate.headline,
      whatHappened: `[FIXTURE] Placeholder description of what happened, from ${candidate.sourceName}.`,
      whyItMatters: '[FIXTURE] Placeholder reasoning for NZ relevance.',
      memberImpact: '[FIXTURE] Placeholder member impact assessment.',
      signalStrength: candidate.signalStrength,
      sourceConfidence: candidate.sourceConfidence,
      verificationStatus: candidate.verificationStatus,
      recommendedCeoAction: '[FIXTURE] Placeholder recommended CEO action.',
      recommendedMemberAction: '[FIXTURE] Placeholder recommended member action.',
      primarySourceUrl: `https://example.test/fixture-source-${index + 1}`,
      registerRouting: 'Action Register',
      nextTriggerDate: '2026-08-06',
    }))

  const officialCount = selectedCandidates.filter((c) => c.sourceConfidence === 'Official').length
  const mediaCount = selectedCandidates.filter((c) => c.sourceConfidence === 'Media').length

  return {
    sourceConfidenceSummary:
      criticalHighSignals.length > 0
        ? '[FIXTURE] Mixed official and media confidence across today\'s selection.'
        : '[FIXTURE] No Critical/High signal in today\'s selection.',
    sourceMix: `[FIXTURE] Official ${officialCount} · Institutional 0 · Sector 0 · Media ${mediaCount}`,
    sections: [
      {
        id: 'sec-1',
        title: '1. Executive judgement',
        content:
          '[FIXTURE] Placeholder executive judgement for UI development — not a real INZBC assessment.',
        reviewStatus: 'pending',
        flagReason: '',
      },
      {
        id: 'sec-2',
        title: '2. Executive summary',
        content:
          '[FIXTURE] - Placeholder bullet one.\n[FIXTURE] - Placeholder bullet two.\n[FIXTURE] - Placeholder bullet three.',
        reviewStatus: 'pending',
        flagReason: '',
      },
      {
        id: 'sec-4',
        title: '4. Key bilateral developments',
        content: '[FIXTURE] Placeholder bilateral development text.',
        reviewStatus: 'pending',
        flagReason: '',
      },
      {
        id: 'sec-5',
        title: '5. Opportunities',
        content: '[FIXTURE] Placeholder opportunity text.',
        reviewStatus: 'pending',
        flagReason: '',
      },
      {
        id: 'sec-6',
        title: '6. Threats and risks',
        content: '[FIXTURE] Placeholder threat/risk text.',
        reviewStatus: 'pending',
        flagReason: '',
      },
      {
        id: 'sec-8',
        title: '8. Member actions',
        content: '[FIXTURE] Placeholder member action text.',
        reviewStatus: 'pending',
        flagReason: '',
      },
      {
        id: 'sec-9',
        title: '9. Watch-list updates',
        content: '[FIXTURE] ACT-009: no change. WL-006: no verified NZ-specific trigger.',
        reviewStatus: 'pending',
        flagReason: '',
      },
      {
        id: 'sec-10',
        title: '10. Active Carry-Forward',
        content: '[FIXTURE] No items carried forward in this placeholder run.',
        reviewStatus: 'pending',
        flagReason: '',
      },
    ],
    criticalHighSignals,
    ceoActionList:
      criticalHighSignals.length > 0
        ? [
            {
              id: 'action-1',
              action: '[FIXTURE] Placeholder CEO action item.',
              owner: '[FIXTURE] Owner TBD',
              priority: 'High',
              dueDate: '2026-08-06',
              evidenceRequirement: '[FIXTURE] Placeholder evidence requirement.',
            },
          ]
        : [],
  }
}

export function newDraftReportFixture(): DailyBriefReport {
  return {
    id: 'report-fixture-1',
    runId: 'RUN-20260730-01',
    runVersion: 0,
    reportVersionId: null,
    reportDate: '2026-07-30',
    coverageStart: '2026-07-29',
    coverageEnd: '2026-07-30',
    generatedAt: '',
    analyst: 'Sunil',
    reviewer: 'Paras',
    reportVersion: 'v1',
    approvedVersionSet: 'SIP-050 v1.1, DB v1.9, SIP-185/186/188 v0.9',
    sourceConfidenceSummary: '',
    sourceMix: '',
    state: 'Report Drafted',
    focusNote: '',
    selectedCandidateIds: [],
    sections: [
      { id: 'sec-1', title: '1. Executive judgement', content: '', reviewStatus: 'pending', flagReason: '' },
      { id: 'sec-2', title: '2. Executive summary', content: '', reviewStatus: 'pending', flagReason: '' },
      {
        id: 'sec-4',
        title: '4. Key bilateral developments',
        content: '',
        reviewStatus: 'pending',
        flagReason: '',
      },
      { id: 'sec-5', title: '5. Opportunities', content: '', reviewStatus: 'pending', flagReason: '' },
      { id: 'sec-6', title: '6. Threats and risks', content: '', reviewStatus: 'pending', flagReason: '' },
      { id: 'sec-8', title: '8. Member actions', content: '', reviewStatus: 'pending', flagReason: '' },
      { id: 'sec-9', title: '9. Watch-list updates', content: '', reviewStatus: 'pending', flagReason: '' },
      {
        id: 'sec-10',
        title: '10. Active Carry-Forward',
        content: '',
        reviewStatus: 'pending',
        flagReason: '',
      },
    ],
    criticalHighSignals: [],
    ceoActionList: [],
    sourceCoverage: sourceCoverageFixture(),
    noMaterialNewSignal: false,
    qaChecklist: qaChecklistFixture(),
    qa: null,
    decision: null,
    distribution: null,
  }
}

export interface ArchivedRunSummary {
  runId: string
  reportDate: string
  state: string
  qaResult: 'Pass' | 'Fail' | null
  decision: string | null
  distributionAuthorised: boolean | null
}

/**
 * Stand-in for a past-runs list — docs/sip-ui-spec.md doesn't specify Screen 4's archive in
 * detail beyond "the executive dashboard the distribution-status view draws on"
 * (`docs/modules/dashboards.md`), and there is no `GET /api/reports` list endpoint built to pull
 * real history from (same "not built yet" gap as every other fixture in this file). Every run
 * below is invented placeholder data for UI development, `[FIXTURE]`-prefixed on the run id so it
 * can never be mistaken for a real historical record.
 */
export function archiveFixture(): ArchivedRunSummary[] {
  return [
    {
      runId: '[FIXTURE] RUN-20260729-01',
      reportDate: '2026-07-29',
      state: 'Distributed',
      qaResult: 'Pass',
      decision: 'continue',
      distributionAuthorised: true,
    },
    {
      runId: '[FIXTURE] RUN-20260728-01',
      reportDate: '2026-07-28',
      state: 'Continue',
      qaResult: 'Pass',
      decision: 'continue',
      distributionAuthorised: false,
    },
    {
      runId: '[FIXTURE] RUN-20260727-01',
      reportDate: '2026-07-27',
      state: 'Report Drafted',
      qaResult: 'Fail',
      decision: null,
      distributionAuthorised: null,
    },
  ]
}
