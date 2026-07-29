import type { DailyBriefReport } from '../domain'

export const FOCUS_NOTE_MAX_LENGTH = 300

/**
 * docs/sip-ui-spec.md Screen 1: "Section 12 cannot be submitted with a blank outcome against an
 * applicable mandatory source — the UI blocks submission and points at the missing source,
 * mirroring the 'blank is a Critical stop' rule in operator-guide.md Step 4. The server still
 * re-checks this; the UI block is a courtesy, not the enforcement point."
 *
 * Returns human-readable error messages; an empty array means the brief may be submitted for QA.
 */
export function validateBrief(report: DailyBriefReport, selectedCandidateCount: number): string[] {
  const errors: string[] = []

  if (!report.reportDate) errors.push('Report / brief date is required.')
  if (!report.coverageStart) errors.push('Coverage window start is required.')
  if (!report.coverageEnd) errors.push('Coverage window end is required.')
  if (report.coverageStart && report.coverageEnd && report.coverageStart > report.coverageEnd) {
    errors.push('Coverage window start must not be after the end.')
  }
  if (selectedCandidateCount === 0) {
    errors.push('At least one scored candidate must be selected to build the brief.')
  }
  if (report.focusNote.length > FOCUS_NOTE_MAX_LENGTH) {
    errors.push(`Focus note exceeds ${FOCUS_NOTE_MAX_LENGTH} characters.`)
  }

  const blankMandatorySources = report.sourceCoverage.filter((row) => row.mandatory && row.outcome === '')
  for (const row of blankMandatorySources) {
    errors.push(`Source coverage: "${row.sourceName}" is a mandatory source with no recorded outcome.`)
  }

  return errors
}
