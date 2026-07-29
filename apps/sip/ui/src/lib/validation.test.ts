import { describe, expect, it } from 'vitest'
import { newDraftReportFixture } from './fixtures'
import { FOCUS_NOTE_MAX_LENGTH, validateBrief } from './validation'

function validBrief() {
  const report = newDraftReportFixture()
  report.sourceCoverage = report.sourceCoverage.map((row) => ({ ...row, outcome: 'Included' }))
  return report
}

describe('validateBrief', () => {
  it('passes a fully completed brief with at least one candidate selected', () => {
    expect(validateBrief(validBrief(), 1)).toEqual([])
  })

  it('requires the report date, coverage start and coverage end', () => {
    const report = validBrief()
    report.reportDate = ''
    report.coverageStart = ''
    report.coverageEnd = ''
    const errors = validateBrief(report, 1)
    expect(errors).toContain('Report / brief date is required.')
    expect(errors).toContain('Coverage window start is required.')
    expect(errors).toContain('Coverage window end is required.')
  })

  it('rejects a coverage window where start is after end', () => {
    const report = validBrief()
    report.coverageStart = '2026-08-05'
    report.coverageEnd = '2026-08-01'
    expect(validateBrief(report, 1)).toContain('Coverage window start must not be after the end.')
  })

  it('requires at least one selected candidate', () => {
    expect(validateBrief(validBrief(), 0)).toContain(
      'At least one scored candidate must be selected to build the brief.',
    )
  })

  it('enforces the focus-note character limit', () => {
    const report = validBrief()
    report.focusNote = 'x'.repeat(FOCUS_NOTE_MAX_LENGTH + 1)
    expect(validateBrief(report, 1)).toContain(`Focus note exceeds ${FOCUS_NOTE_MAX_LENGTH} characters.`)
  })

  it('blocks on any mandatory source with a blank outcome, naming it', () => {
    const report = validBrief()
    const blankRow = report.sourceCoverage[0]!
    report.sourceCoverage = [{ ...blankRow, outcome: '' }, ...report.sourceCoverage.slice(1)]
    const errors = validateBrief(report, 1)
    expect(errors).toContain(
      `Source coverage: "${blankRow.sourceName}" is a mandatory source with no recorded outcome.`,
    )
  })

  it('does not block on a non-mandatory source with a blank outcome', () => {
    const report = validBrief()
    const row = report.sourceCoverage[0]!
    report.sourceCoverage = [{ ...row, mandatory: false, outcome: '' }, ...report.sourceCoverage.slice(1)]
    const errors = validateBrief(report, 1)
    expect(errors.some((message) => message.includes(row.sourceName))).toBe(false)
  })
})
