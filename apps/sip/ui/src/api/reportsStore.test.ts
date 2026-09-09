import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { DailyBriefReport, QaChecklistGroup } from '../domain'
import { candidatesFixture, newDraftReportFixture, qaChecklistFixture } from '../lib/fixtures'
import {
  authoriseDistribution,
  recordCeoDecision,
  returnForCorrection,
  ReportsApiError,
  submitQaResult,
  submitReportForQa,
} from './reportsStore'
import { stubReportsFetch } from './reportsStore.testSupport'
import { clearSession } from './session'

function submittableReport() {
  const report = newDraftReportFixture()
  report.sourceCoverage = report.sourceCoverage.map((row) => ({ ...row, outcome: 'Included' }))
  report.selectedCandidateIds = ['cand-1']
  return report
}

// `submitQaResult` now needs the report_version_id `POST /api/reports` would have assigned — a
// fixture built directly, without going through `submitReportForQa` first, stands one in for it.
function inProgressReport(overrides: Partial<DailyBriefReport> = {}): DailyBriefReport {
  return { ...submittableReport(), state: 'QA In Progress', reportVersionId: 'rv-1', ...overrides }
}

function allPassingChecklist(): QaChecklistGroup[] {
  return qaChecklistFixture().map((group) => ({
    ...group,
    items: group.items.map((item) => ({ ...item, answer: 'pass' as const })),
  }))
}

// Session/CSRF plumbing needs no stub: vitest.setup.ts seeds a session directly, so getCsrfToken
// never fetches — only the three real endpoints below (stubReportsFetch) need a response.
beforeEach(() => {
  stubReportsFetch()
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('submitReportForQa', () => {
  it('transitions Report Drafted -> QA In Progress once the brief is valid', async () => {
    const result = await submitReportForQa(submittableReport(), candidatesFixture())
    expect(result.state).toBe('QA In Progress')
  })

  it("sends the run's UUID as run_id, never its run number", async () => {
    // The server validates `SubmitReportIn.run_id` as a UUID against `runs.id`. Sending a run
    // number is not a validation error there, it is a 500 out of psycopg, so this is worth
    // pinning: the two values now live in separate fields precisely so this cannot be confused.
    const report = { ...submittableReport(), runId: 'f2b3c7e1-0000-4000-8000-000000000001', runNumber: 'RUN-SEED-06' }
    await submitReportForQa(report, candidatesFixture())

    const [, init] = vi.mocked(fetch).mock.calls.find(([url]) => url === '/api/reports')!
    expect(JSON.parse(String(init?.body)).run_id).toBe('f2b3c7e1-0000-4000-8000-000000000001')
  })

  it("hashes the candidates it was given, not a stand-in for them", async () => {
    // The digest used to be resolved against candidatesFixture(), whose ids cannot match a live
    // candidate's UUID -- so nothing resolved and every brief was hashed as if empty. Two
    // different selections must not produce the same hash.
    const one = { ...submittableReport(), selectedCandidateIds: ['cand-1'] }
    const two = { ...submittableReport(), selectedCandidateIds: ['cand-1', 'cand-2'] }

    await submitReportForQa(one, candidatesFixture())
    const first = JSON.parse(String(vi.mocked(fetch).mock.calls.at(-1)?.[1]?.body)).content_sha256
    await submitReportForQa(two, candidatesFixture())
    const second = JSON.parse(String(vi.mocked(fetch).mock.calls.at(-1)?.[1]?.body)).content_sha256

    expect(first).not.toBe(second)
  })

  it("refuses a selection it cannot resolve rather than hashing a shorter list", async () => {
    // A selected id with no candidate means the list being hashed is not the list that was
    // chosen. Dropping it silently would submit a brief that understates what it contains.
    const report = { ...submittableReport(), selectedCandidateIds: ['cand-1', 'not-a-candidate'] }
    await expect(submitReportForQa(report, candidatesFixture())).rejects.toThrow(/not in the list/i)
  })

  it('rejects when the brief still fails validation, without transitioning', async () => {
    await expect(submitReportForQa(newDraftReportFixture(), candidatesFixture())).rejects.toBeInstanceOf(ReportsApiError)
  })

  it('rejects submitting from a state other than Report Drafted', async () => {
    const report = { ...submittableReport(), state: 'QA In Progress' as const }
    await expect(submitReportForQa(report, candidatesFixture())).rejects.toThrow(/cannot submit for qa/i)
  })

  it('propagates an abort rather than a service error', async () => {
    const controller = new AbortController()
    const promise = submitReportForQa(submittableReport(), candidatesFixture(), { signal: controller.signal })
    controller.abort()
    await expect(promise).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('reports "not signed in" distinctly, rather than a generic unreachable-service message', async () => {
    clearSession()
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url === '/api/session') return { ok: false, status: 401, json: async () => null } as Response
      throw new Error(`Unexpected fetch in test: ${url}`)
    }))

    await expect(submitReportForQa(submittableReport(), candidatesFixture())).rejects.toThrow(/not signed in/i)
  })

  it('only carries signals for the candidates actually selected, not a fixed pair', async () => {
    const report = { ...submittableReport(), selectedCandidateIds: ['cand-3'] } // Medium, non-Critical/High
    const result = await submitReportForQa(report, candidatesFixture())
    expect(result.criticalHighSignals).toEqual([])
  })

  it('carries a signal for a selected Critical candidate', async () => {
    const report = { ...submittableReport(), selectedCandidateIds: ['cand-2'] } // Critical ministerial statement
    const result = await submitReportForQa(report, candidatesFixture())
    expect(result.criticalHighSignals).toHaveLength(1)
    expect(result.criticalHighSignals[0]!.headline).toMatch(/ministerial statement/i)
  })
})

describe('submitQaResult', () => {
  it('passes and moves to Awaiting CEO Decision when every item passes', async () => {
    const result = await submitQaResult(inProgressReport(), allPassingChecklist(), 'Paras', 'Checked all sections.')
    expect(result.state).toBe('Awaiting CEO Decision')
    expect(result.qa?.result).toBe('Pass')
  })

  it('fails and moves to QA Failed on any Critical item marked fail', async () => {
    const checklist = allPassingChecklist()
    checklist[0]!.items[1] = { ...checklist[0]!.items[1]!, answer: 'fail' }
    const result = await submitQaResult(inProgressReport(), checklist, 'Paras', 'a2 failed verification.')
    expect(result.state).toBe('QA Failed')
    expect(result.qa?.result).toBe('Fail')
    expect(result.qa?.criticalFailuresFound).not.toBe('')
  })

  it('rejects when the reviewer is the run\'s own analyst', async () => {
    const report = inProgressReport({ analyst: 'Sunil' })
    await expect(
      submitQaResult(report, allPassingChecklist(), 'Sunil', 'Checked all sections.'),
    ).rejects.toThrow(/cannot be this run/i)
  })

  it('rejects a blank reviewer rather than silently skipping the analyst check', async () => {
    const report = inProgressReport()
    await expect(submitQaResult(report, allPassingChecklist(), '', 'notes')).rejects.toThrow(/reviewer is required/i)
    await expect(submitQaResult(report, allPassingChecklist(), '   ', 'notes')).rejects.toThrow(
      /reviewer is required/i,
    )
  })

  it('rejects an empty checklist rather than treating it as fully passed', async () => {
    const report = inProgressReport()
    await expect(submitQaResult(report, [], 'Paras', 'notes')).rejects.toThrow(/checklist is empty/i)
    await expect(
      submitQaResult(report, [{ id: 'g', title: 'g', items: [] }], 'Paras', 'notes'),
    ).rejects.toThrow(/checklist is empty/i)
  })

  it('rejects blank QA notes rather than recording a result with nothing to show for it', async () => {
    const report = inProgressReport()
    await expect(submitQaResult(report, allPassingChecklist(), 'Paras', '')).rejects.toThrow(/notes are required/i)
    await expect(submitQaResult(report, allPassingChecklist(), 'Paras', '   ')).rejects.toThrow(
      /notes are required/i,
    )
  })

  it('rejects when the report has not been submitted yet (no report_version_id)', async () => {
    const report = inProgressReport({ reportVersionId: null })
    await expect(
      submitQaResult(report, allPassingChecklist(), 'Paras', 'Checked all sections.'),
    ).rejects.toThrow(/has not been submitted/i)
  })

  it('treats N/A on a Critical item as a failure, not a pass', async () => {
    const checklist = allPassingChecklist()
    checklist[0]!.items[1] = { ...checklist[0]!.items[1]!, answer: 'na' } // a2, critical: true
    const result = await submitQaResult(inProgressReport(), checklist, 'Paras', 'a2 not applicable.')
    expect(result.state).toBe('QA Failed')
    expect(result.qa?.result).toBe('Fail')
    expect(result.qa?.criticalFailuresFound).not.toBe('')
  })

  it('rejects recording a QA result outside QA In Progress', async () => {
    const report = { ...submittableReport(), state: 'Report Drafted' as const }
    await expect(
      submitQaResult(report, allPassingChecklist(), 'Paras', 'notes'),
    ).rejects.toBeInstanceOf(ReportsApiError)
  })
})

describe('returnForCorrection', () => {
  it("moves QA Failed back to Report Drafted, carrying the run's new version", async () => {
    const report = { ...submittableReport(), state: 'QA Failed' as const }
    const result = await returnForCorrection(report)
    expect(result.state).toBe('Report Drafted')
    // The transition bumps the run's version, and the next write has to cite the new one.
    // Returning the report unchanged here would make the following call fail as stale.
    expect(result.runVersion).toBe(2)
  })

  it('rejects from any other state', async () => {
    const report = { ...submittableReport(), state: 'Report Drafted' as const }
    await expect(returnForCorrection(report)).rejects.toBeInstanceOf(ReportsApiError)
  })
})

describe('recordCeoDecision', () => {
  function awaitingDecisionReport() {
    return { ...submittableReport(), state: 'Awaiting CEO Decision' as const, reportVersionId: 'rv-1' }
  }
  function baseDecision(overrides: Partial<Parameters<typeof recordCeoDecision>[1]> = {}) {
    return {
      reportVersion: 'v0.9 Review Draft',
      decision: 'continue' as const,
      reason: 'On track',
      conditions: '',
      owner: 'Sunil',
      evidenceReference: 'Doc ref 123',
      nextReviewDate: '2026-08-01',
      decidedAt: new Date().toISOString(),
      ...overrides,
    }
  }

  it('maps stop -> Stopped', async () => {
    const result = await recordCeoDecision(awaitingDecisionReport(), baseDecision({ decision: 'stop' }))
    expect(result.state).toBe('Stopped')
  })

  it('maps pause -> Paused', async () => {
    const result = await recordCeoDecision(awaitingDecisionReport(), baseDecision({ decision: 'pause' }))
    expect(result.state).toBe('Paused')
  })

  it('maps continue -> Continue, leaving distribution undecided (a separate action)', async () => {
    const result = await recordCeoDecision(awaitingDecisionReport(), baseDecision({ decision: 'continue' }))
    expect(result.state).toBe('Continue')
    expect(result.decision?.distributionAuthorised).toBeNull()
    expect(result.decision?.distributionDecidedAt).toBeNull()
  })

  it('rejects recording a decision outside Awaiting CEO Decision', async () => {
    const report = { ...submittableReport(), state: 'QA In Progress' as const }
    await expect(recordCeoDecision(report, baseDecision())).rejects.toBeInstanceOf(ReportsApiError)
  })

  it('rejects a null decision type', async () => {
    await expect(
      recordCeoDecision(awaitingDecisionReport(), baseDecision({ decision: null })),
    ).rejects.toThrow(/report decision.*is required/i)
  })

  it('rejects blank required fields rather than relying solely on the UI\'s disabled button', async () => {
    await expect(
      recordCeoDecision(awaitingDecisionReport(), baseDecision({ reportVersion: '' })),
    ).rejects.toThrow(/report version.*is required/i)
    await expect(recordCeoDecision(awaitingDecisionReport(), baseDecision({ reason: '' }))).rejects.toThrow(
      /reason.*is required/i,
    )
    await expect(recordCeoDecision(awaitingDecisionReport(), baseDecision({ owner: '' }))).rejects.toThrow(
      /owner.*is required/i,
    )
    await expect(
      recordCeoDecision(awaitingDecisionReport(), baseDecision({ evidenceReference: '' })),
    ).rejects.toThrow(/evidence reference.*is required/i)
    await expect(
      recordCeoDecision(awaitingDecisionReport(), baseDecision({ nextReviewDate: '' })),
    ).rejects.toThrow(/next review date.*is required/i)
    await expect(
      recordCeoDecision(awaitingDecisionReport(), baseDecision({ decidedAt: null })),
    ).rejects.toThrow(/decision timestamp.*is required/i)
  })

  it('does not require conditions — the field is genuinely optional', async () => {
    const result = await recordCeoDecision(awaitingDecisionReport(), baseDecision({ conditions: '' }))
    expect(result.state).toBe('Continue')
  })
})

describe('authoriseDistribution', () => {
  async function reportWithDecision(decision: 'continue' | 'continue_with_correction' = 'continue') {
    const report = {
      ...submittableReport(),
      state: 'Awaiting CEO Decision' as const,
      reportVersionId: 'rv-1',
    }
    return recordCeoDecision(report, {
      reportVersion: 'v0.9 Review Draft',
      decision,
      reason: 'On track',
      conditions: '',
      owner: 'Sunil',
      evidenceReference: 'Doc ref 123',
      nextReviewDate: '2026-08-01',
      decidedAt: new Date().toISOString(),
    })
  }

  it('authorised -> Approved for Manual Distribution', async () => {
    const decided = await reportWithDecision('continue')
    const result = await authoriseDistribution(decided, true)
    expect(result.state).toBe('Approved for Manual Distribution')
    expect(result.decision?.distributionAuthorised).toBe(true)
  })

  it('not authorised -> stays Continue, a complete outcome rather than an error', async () => {
    const decided = await reportWithDecision('continue')
    const result = await authoriseDistribution(decided, false)
    expect(result.state).toBe('Continue')
    expect(result.decision?.distributionAuthorised).toBe(false)
    expect(result.decision?.distributionDecidedAt).not.toBeNull()
  })

  it('refuses Authorised from Continue With Correction — ADR-0005 accepts it only on Continue', async () => {
    const decided = await reportWithDecision('continue_with_correction')
    await expect(authoriseDistribution(decided, true)).rejects.toThrow(/ADR-0005 permits Authorised/i)
  })

  it('still allows Not Authorised from Continue With Correction — refusing is always valid', async () => {
    const decided = await reportWithDecision('continue_with_correction')
    const result = await authoriseDistribution(decided, false)
    expect(result.decision?.distributionAuthorised).toBe(false)
  })

  it('rejects before a report decision has been recorded', async () => {
    const report = { ...submittableReport(), state: 'Awaiting CEO Decision' as const }
    await expect(authoriseDistribution(report, true)).rejects.toThrow(/before a report decision/i)
  })

  it('rejects deciding distribution twice', async () => {
    const decided = await reportWithDecision('continue')
    const once = await authoriseDistribution(decided, false)
    await expect(authoriseDistribution(once, true)).rejects.toThrow(/already been decided/i)
  })

  it('rejects from Paused — a paused/stopped run never reaches a distribution question', async () => {
    const report = {
      ...submittableReport(),
      state: 'Awaiting CEO Decision' as const,
      reportVersionId: 'rv-1',
    }
    const paused = await recordCeoDecision(report, {
      reportVersion: 'v0.9 Review Draft',
      decision: 'pause',
      reason: 'Waiting on confirmation',
      conditions: '',
      owner: 'Sunil',
      evidenceReference: 'Doc ref 123',
      nextReviewDate: '2026-08-01',
      decidedAt: new Date().toISOString(),
    })
    await expect(authoriseDistribution(paused, true)).rejects.toThrow(/cannot authorise distribution/i)
  })
})
