import { describe, expect, it } from 'vitest'
import type { QaChecklistGroup } from '../domain'
import { newDraftReportFixture, qaChecklistFixture } from '../lib/fixtures'
import {
  authoriseDistribution,
  recordCeoDecision,
  returnForCorrection,
  ReportsApiError,
  submitQaResult,
  submitReportForQa,
} from './reportsStore'

function submittableReport() {
  const report = newDraftReportFixture()
  report.sourceCoverage = report.sourceCoverage.map((row) => ({ ...row, outcome: 'Included' }))
  report.selectedCandidateIds = ['cand-1']
  return report
}

function allPassingChecklist(): QaChecklistGroup[] {
  return qaChecklistFixture().map((group) => ({
    ...group,
    items: group.items.map((item) => ({ ...item, answer: 'pass' as const })),
  }))
}

describe('submitReportForQa', () => {
  it('transitions Report Drafted -> QA In Progress once the brief is valid', async () => {
    const result = await submitReportForQa(submittableReport())
    expect(result.state).toBe('QA In Progress')
  })

  it('rejects when the brief still fails validation, without transitioning', async () => {
    await expect(submitReportForQa(newDraftReportFixture())).rejects.toBeInstanceOf(ReportsApiError)
  })

  it('rejects submitting from a state other than Report Drafted', async () => {
    const report = { ...submittableReport(), state: 'QA In Progress' as const }
    await expect(submitReportForQa(report)).rejects.toThrow(/cannot submit for qa/i)
  })

  it('propagates an abort rather than a service error', async () => {
    const controller = new AbortController()
    const promise = submitReportForQa(submittableReport(), { signal: controller.signal })
    controller.abort()
    await expect(promise).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('only carries signals for the candidates actually selected, not a fixed pair', async () => {
    const report = { ...submittableReport(), selectedCandidateIds: ['cand-3'] } // Medium, non-Critical/High
    const result = await submitReportForQa(report)
    expect(result.criticalHighSignals).toEqual([])
  })

  it('carries a signal for a selected Critical candidate', async () => {
    const report = { ...submittableReport(), selectedCandidateIds: ['cand-2'] } // Critical ministerial statement
    const result = await submitReportForQa(report)
    expect(result.criticalHighSignals).toHaveLength(1)
    expect(result.criticalHighSignals[0]!.headline).toMatch(/ministerial statement/i)
  })
})

describe('submitQaResult', () => {
  it('passes and moves to Awaiting CEO Decision when every item passes', async () => {
    const report = { ...submittableReport(), state: 'QA In Progress' as const }
    const result = await submitQaResult(report, allPassingChecklist(), 'Paras')
    expect(result.state).toBe('Awaiting CEO Decision')
    expect(result.qa?.result).toBe('Pass')
  })

  it('fails and moves to QA Failed on any Critical item marked fail', async () => {
    const report = { ...submittableReport(), state: 'QA In Progress' as const }
    const checklist = allPassingChecklist()
    checklist[0]!.items[1] = { ...checklist[0]!.items[1]!, answer: 'fail' }
    const result = await submitQaResult(report, checklist, 'Paras')
    expect(result.state).toBe('QA Failed')
    expect(result.qa?.result).toBe('Fail')
    expect(result.qa?.criticalFailuresFound).not.toBe('')
  })

  it('rejects when the reviewer is the run\'s own analyst', async () => {
    const report = { ...submittableReport(), state: 'QA In Progress' as const, analyst: 'Sunil' }
    await expect(submitQaResult(report, allPassingChecklist(), 'Sunil')).rejects.toThrow(/cannot be this run/i)
  })

  it('rejects a blank reviewer rather than silently skipping the analyst check', async () => {
    const report = { ...submittableReport(), state: 'QA In Progress' as const }
    await expect(submitQaResult(report, allPassingChecklist(), '')).rejects.toThrow(/reviewer is required/i)
    await expect(submitQaResult(report, allPassingChecklist(), '   ')).rejects.toThrow(/reviewer is required/i)
  })

  it('rejects an empty checklist rather than treating it as fully passed', async () => {
    const report = { ...submittableReport(), state: 'QA In Progress' as const }
    await expect(submitQaResult(report, [], 'Paras')).rejects.toThrow(/checklist is empty/i)
    await expect(submitQaResult(report, [{ id: 'g', title: 'g', items: [] }], 'Paras')).rejects.toThrow(
      /checklist is empty/i,
    )
  })

  it('treats N/A on a Critical item as a failure, not a pass', async () => {
    const report = { ...submittableReport(), state: 'QA In Progress' as const }
    const checklist = allPassingChecklist()
    checklist[0]!.items[1] = { ...checklist[0]!.items[1]!, answer: 'na' } // a2, critical: true
    const result = await submitQaResult(report, checklist, 'Paras')
    expect(result.state).toBe('QA Failed')
    expect(result.qa?.result).toBe('Fail')
    expect(result.qa?.criticalFailuresFound).not.toBe('')
  })

  it('rejects recording a QA result outside QA In Progress', async () => {
    const report = { ...submittableReport(), state: 'Report Drafted' as const }
    await expect(submitQaResult(report, allPassingChecklist(), 'Paras')).rejects.toBeInstanceOf(ReportsApiError)
  })
})

describe('returnForCorrection', () => {
  it('moves QA Failed back to Report Drafted', async () => {
    const report = { ...submittableReport(), state: 'QA Failed' as const }
    const result = await returnForCorrection(report)
    expect(result.state).toBe('Report Drafted')
  })

  it('rejects from any other state', async () => {
    const report = { ...submittableReport(), state: 'Report Drafted' as const }
    await expect(returnForCorrection(report)).rejects.toBeInstanceOf(ReportsApiError)
  })
})

describe('recordCeoDecision', () => {
  function awaitingDecisionReport() {
    return { ...submittableReport(), state: 'Awaiting CEO Decision' as const }
  }
  function baseDecision(overrides: Partial<Parameters<typeof recordCeoDecision>[1]> = {}) {
    return {
      reportVersion: 'v0.9 Review Draft',
      decision: 'continue' as const,
      reason: 'On track',
      conditions: '',
      owner: 'Sunil',
      evidenceReference: '',
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
})

describe('authoriseDistribution', () => {
  async function reportWithDecision(decision: 'continue' | 'continue_with_correction' = 'continue') {
    const report = { ...submittableReport(), state: 'Awaiting CEO Decision' as const }
    return recordCeoDecision(report, {
      reportVersion: 'v0.9 Review Draft',
      decision,
      reason: 'On track',
      conditions: '',
      owner: 'Sunil',
      evidenceReference: '',
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

  it('works from Continue With Correction too', async () => {
    const decided = await reportWithDecision('continue_with_correction')
    const result = await authoriseDistribution(decided, true)
    expect(result.state).toBe('Approved for Manual Distribution')
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
    const report = { ...submittableReport(), state: 'Awaiting CEO Decision' as const }
    const paused = await recordCeoDecision(report, {
      reportVersion: 'v0.9 Review Draft',
      decision: 'pause',
      reason: 'Waiting on confirmation',
      conditions: '',
      owner: 'Sunil',
      evidenceReference: '',
      nextReviewDate: '2026-08-01',
      decidedAt: new Date().toISOString(),
    })
    await expect(authoriseDistribution(paused, true)).rejects.toThrow(/cannot authorise distribution/i)
  })
})
