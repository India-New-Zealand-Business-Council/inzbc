/**
 * Contract fixtures for local development and tests — not real INZBC intelligence output.
 *
 * Source *names* below are the real SIP-185 mandatory source register
 * (docs/sip/launch/SIP-185_source_register_v0.9.md) — organisation names, not statistics, so
 * reusing them keeps the source-coverage table meaningful. Every headline, judgement and signal
 * below is invented placeholder text for UI development, per CLAUDE.md's "never invent
 * statistics, member counts, board names, or FTA details" — each is prefixed `[FIXTURE]` so it
 * can never be mistaken for real output if this ever renders somewhere unexpected.
 */

import type { Candidate, DailyBriefReport, QaChecklistGroup, SourceCoverageRow } from '../domain'

export const MANDATORY_SOURCES: { id: string; sip185Code: string; name: string }[] = [
  { id: 'src-mfat', sip185Code: 'OFF-NZ-MFAT', name: 'MFAT' },
  { id: 'src-beehive', sip185Code: 'OFF-NZ-BEEHIVE', name: 'Beehive / ministerial releases' },
  { id: 'src-customs', sip185Code: 'OFF-NZ-CUSTOMS', name: 'NZ Customs' },
  { id: 'src-pib', sip185Code: 'OFF-IN-PIB', name: 'Ministry of Commerce & Industry / PIB' },
  { id: 'src-dgft', sip185Code: 'OFF-IN-DGFT', name: 'DGFT' },
  { id: 'src-nzherald', sip185Code: 'MEDIA-NZ-HERALD', name: 'NZ Herald' },
  { id: 'src-rnz', sip185Code: 'MEDIA-NZ-RNZ', name: 'RNZ' },
  { id: 'src-stuff', sip185Code: 'MEDIA-NZ-STUFF', name: 'Stuff' },
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
      sourceName: 'MFAT',
      sip185Code: 'OFF-NZ-MFAT',
      sector: 'Dairy',
      signalStrength: 'High',
      sourceConfidence: 'Official',
      verificationStatus: 'Verified',
    },
    {
      id: 'cand-2',
      headline: '[FIXTURE] Ministerial statement on bilateral trade talks',
      sourceName: 'Beehive / ministerial releases',
      sip185Code: 'OFF-NZ-BEEHIVE',
      sector: 'Bilateral',
      signalStrength: 'Critical',
      sourceConfidence: 'Official',
      verificationStatus: 'Verified',
    },
    {
      id: 'cand-3',
      headline: '[FIXTURE] Sector commentary on wool market conditions',
      sourceName: 'RNZ',
      sip185Code: 'MEDIA-NZ-RNZ',
      sector: 'Wool',
      signalStrength: 'Medium',
      sourceConfidence: 'Media',
      verificationStatus: 'Unverified',
    },
    {
      id: 'cand-4',
      headline: '[FIXTURE] DGFT notice referenced in import-compliance monitoring',
      sourceName: 'DGFT',
      sip185Code: 'OFF-IN-DGFT',
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
          text: 'Distribution authority correct; recipient limited to the authorised recipient on file.',
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
 */
export function generatedDigestContent(): Pick<
  DailyBriefReport,
  'sections' | 'criticalHighSignals' | 'ceoActionList' | 'sourceConfidenceSummary' | 'sourceMix'
> {
  return {
    sourceConfidenceSummary: '[FIXTURE] Mixed official and media confidence across today\'s selection.',
    sourceMix: '[FIXTURE] Official 2 · Institutional 0 · Sector 0 · Media 2',
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
    criticalHighSignals: [
      {
        id: 'signal-1',
        headline: '[FIXTURE] Ministerial statement on bilateral trade talks',
        whatHappened: '[FIXTURE] Placeholder description of what happened.',
        whyItMatters: '[FIXTURE] Placeholder reasoning for NZ relevance.',
        memberImpact: '[FIXTURE] Placeholder member impact assessment.',
        signalStrength: 'Critical',
        sourceConfidence: 'Official',
        verificationStatus: 'Verified',
        recommendedCeoAction: '[FIXTURE] Placeholder recommended CEO action.',
        recommendedMemberAction: '[FIXTURE] Placeholder recommended member action.',
        primarySourceUrl: 'https://example.test/fixture-source-1',
        registerRouting: 'Action Register',
        nextTriggerDate: '2026-08-06',
      },
      {
        id: 'signal-2',
        headline: '[FIXTURE] Tariff schedule update noted for dairy exports',
        whatHappened: '[FIXTURE] Placeholder description of what happened.',
        whyItMatters: '[FIXTURE] Placeholder reasoning for NZ relevance.',
        memberImpact: '[FIXTURE] Placeholder member impact assessment.',
        signalStrength: 'High',
        sourceConfidence: 'Official',
        verificationStatus: 'Verified',
        recommendedCeoAction: '[FIXTURE] Placeholder recommended CEO action.',
        recommendedMemberAction: '[FIXTURE] Placeholder recommended member action.',
        primarySourceUrl: 'https://example.test/fixture-source-2',
        registerRouting: 'Watch Register',
        nextTriggerDate: '2026-08-13',
      },
    ],
    ceoActionList: [
      {
        id: 'action-1',
        action: '[FIXTURE] Placeholder CEO action item.',
        owner: '[FIXTURE] Owner TBD',
        priority: 'High',
        dueDate: '2026-08-06',
        evidenceRequirement: '[FIXTURE] Placeholder evidence requirement.',
      },
    ],
  }
}

export function newDraftReportFixture(): DailyBriefReport {
  return {
    id: 'report-fixture-1',
    runId: 'RUN-20260730-01',
    reportDate: '2026-07-30',
    coverageStart: '2026-07-29',
    coverageEnd: '2026-07-30',
    generatedAt: '',
    analyst: 'Sunil',
    reviewer: 'Paras',
    approvedVersionSet: 'SIP-050 v1.1, DB v1.9, SIP-185/186/188 v0.9',
    sourceConfidenceSummary: '',
    sourceMix: '',
    state: 'Report Drafted',
    focusNote: '',
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
