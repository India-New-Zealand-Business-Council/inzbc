import { describe, expect, it } from 'vitest'
import type { QaChecklistGroup } from '../domain'
import { newDraftReportFixture, qaChecklistFixture } from '../lib/fixtures'
import {
  recordCeoDecision,
  returnForCorrection,
  ReportsApiError,
  submitQaResult,
  submitReportForQa,
} from './reportsStore'

function submittableReport() {
  const report = newDraftReportFixture()
  report.sourceCoverage = report.sourceCoverage.map((row) => ({ ...row, outcome: 'Included' }))
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
    const result = await submitReportForQa(submittableReport(), 1)
    expect(result.state).toBe('QA In Progress')
  })

  it('rejects when the brief still fails validation, without transitioning', async () => {
    await expect(submitReportForQa(newDraftReportFixture(), 0)).rejects.toBeInstanceOf(ReportsApiError)
  })

  it('rejects submitting from a state other than Report Drafted', async () => {
    const report = { ...submittableReport(), state: 'QA In Progress' as const }
    await expect(submitReportForQa(report, 1)).rejects.toThrow(/cannot submit for qa/i)
  })

  it('propagates an abort rather than a service error', async () => {
    const controller = new AbortController()
    const promise = submitReportForQa(submittableReport(), 1, { signal: controller.signal })
    controller.abort()
    await expect(promise).rejects.toMatchObject({ name: 'AbortError' })
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
      distributionAuthorised: null,
      distributionDecidedAt: null,
      ...overrides,
    }
  }

  it('maps stop -> Stopped regardless of distribution authorisation', async () => {
    const result = await recordCeoDecision(awaitingDecisionReport(), baseDecision({ decision: 'stop' }))
    expect(result.state).toBe('Stopped')
  })

  it('maps pause -> Paused', async () => {
    const result = await recordCeoDecision(awaitingDecisionReport(), baseDecision({ decision: 'pause' }))
    expect(result.state).toBe('Paused')
  })

  it('maps continue + distribution authorised -> Approved for Manual Distribution', async () => {
    const result = await recordCeoDecision(
      awaitingDecisionReport(),
      baseDecision({ decision: 'continue', distributionAuthorised: true }),
    )
    expect(result.state).toBe('Approved for Manual Distribution')
  })

  it('maps continue + distribution NOT authorised -> Continue, not an error state', async () => {
    const result = await recordCeoDecision(
      awaitingDecisionReport(),
      baseDecision({ decision: 'continue', distributionAuthorised: false }),
    )
    expect(result.state).toBe('Continue')
  })

  it('rejects recording a decision outside Awaiting CEO Decision', async () => {
    const report = { ...submittableReport(), state: 'QA In Progress' as const }
    await expect(recordCeoDecision(report, baseDecision())).rejects.toBeInstanceOf(ReportsApiError)
  })
})
