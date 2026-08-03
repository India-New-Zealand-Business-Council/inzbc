import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as reportsStore from '../api/reportsStore'
import type { DailyBriefReport } from '../domain'
import { newDraftReportFixture } from '../lib/fixtures'
import { BriefBuilderScreen } from './BriefBuilderScreen'

afterEach(() => vi.restoreAllMocks())

/** A controlled wrapper so interaction tests exercise real state updates, not a static prop. */
function ControlledBriefBuilder({ initial }: { initial: DailyBriefReport }) {
  const [report, setReport] = useState(initial)
  return <BriefBuilderScreen report={report} onChange={setReport} />
}

// All 112 mandatory sources already covered, and a candidate pre-selected — used by tests that
// only care about what happens once the brief is otherwise valid. Setting this directly rather
// than clicking through all 112 outcome selects: they share identical wiring (one spot-check in
// 'records a source-outcome change via onChange' below covers that), so re-driving every row
// through fireEvent per test only multiplies render cost without covering anything new.
function reportReadyForQa(): DailyBriefReport {
  const report = newDraftReportFixture()
  report.sourceCoverage = report.sourceCoverage.map((row) => ({ ...row, outcome: 'Included' }))
  report.selectedCandidateIds = ['cand-1']
  return report
}

describe('BriefBuilderScreen', () => {
  it('renders the run header as read-only data, not editable inputs', () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    const runIdCell = screen.getByText(report.runId)
    expect(runIdCell).toBeInTheDocument()
    expect(screen.getByText(report.analyst)).toBeInTheDocument()
    // Scoped to the run-header <dl>, not screen.queryByLabelText: the full page also carries 112
    // source-coverage rows (a <select> + <input> each, sr-only-labelled), and *ByLabelText's
    // accessible-name computation over that many candidates took ~18s — past this suite's 20s
    // testTimeout — for a query that only ever needed to look at 4 read-only dt/dd pairs.
    const runHeader = runIdCell.closest('dl')
    if (!runHeader) throw new Error('run header <dl> not found')
    expect(within(runHeader).queryByRole('textbox')).not.toBeInTheDocument()
  })

  it('reports a coverage-window edit via onChange without mutating the caller-owned report', async () => {
    const report = newDraftReportFixture()
    const onChange = vi.fn()
    render(<BriefBuilderScreen report={report} onChange={onChange} />)

    // label.control (native DOM, not a Testing Library query) rather than getByLabelText: same
    // 112-row accessible-name-computation cost as the test above — getByLabelText(/coverage
    // window start/i) alone took ~18s here.
    const coverageStartLabel = screen.getByText(/coverage window start/i) as HTMLLabelElement
    const coverageStartInput = coverageStartLabel.control
    if (!coverageStartInput) throw new Error('coverage window start input not found')
    fireEvent.change(coverageStartInput, { target: { value: '2026-08-01' } })

    expect(onChange).toHaveBeenCalled()
    const latestCall = onChange.mock.calls.at(-1)
    if (!latestCall) throw new Error('onChange was not called')
    expect(latestCall[0].coverageStart).toBe('2026-08-01')
    expect(report.coverageStart).not.toBe('2026-08-01')
  })

  it('lists fixture candidates for source selection and tracks the count selected', async () => {
    // Controlled: selection now lives on `report` (lifted state), not inside this component, so
    // seeing the count actually update needs a caller that re-renders with the new report on
    // onChange — a static prop + no-op onChange can't observe it.
    render(<ControlledBriefBuilder initial={newDraftReportFixture()} />)

    expect(screen.getByText('0 candidate(s) selected')).toBeInTheDocument()
    const checkboxes = screen.getAllByRole('checkbox')
    await userEvent.click(checkboxes[0]!)

    expect(screen.getByText('1 candidate(s) selected')).toBeInTheDocument()
  })

  it('candidate selection reports via onChange onto the report, not local state that navigation would wipe', async () => {
    const report = newDraftReportFixture()
    const onChange = vi.fn()
    render(<BriefBuilderScreen report={report} onChange={onChange} />)

    await userEvent.click(screen.getAllByRole('checkbox')[0]!)

    const latestCall = onChange.mock.calls.at(-1)
    if (!latestCall) throw new Error('onChange was not called')
    expect(latestCall[0].selectedCandidateIds).toEqual(['cand-1'])
    expect(report.selectedCandidateIds).toEqual([])
  })

  it('labels the focus note as non-canonical rather than presenting it as a SIP-186 field', () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)
    expect(screen.getByText(/not a sip-186 field/i)).toBeInTheDocument()
  })

  it('carries the governance line — docs/sip-ui-spec.md requires it on every view of the brief', () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)
    expect(
      screen.getByText(/human-reviewed\. not authorised for member, external, website or social publication\./i),
    ).toBeInTheDocument()
  })

  it('stays invalid on blank mandatory sources and no candidate selected, without alarming on load', () => {
    // A fresh brief is invalid by construction (112 blank sources, no candidate yet) — that's
    // expected, not an error state. The detailed box only appears after a submit attempt
    // (hasAttemptedSubmit); on load, this is just the ordinary starting point.
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByText(/ready to submit for qa/i)).not.toBeInTheDocument()
  })

  it('shows the calm progress count instead of the red box before any submit attempt', () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    expect(screen.getByText('0 / 112 sources recorded')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('leaves the Outcome select with a neutral border before any submit attempt', async () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    // Expand a group to reach a still-blank mandatory Outcome select.
    await userEvent.click(screen.getByRole('button', { name: /nz official/i }))
    const outcomeSelect = screen.getAllByRole('combobox')[0]!

    expect(outcomeSelect.className).not.toContain('border-inzbc-crimson')
    expect(outcomeSelect.className).toContain('border-inzbc-navy/20')
  })

  it('still blocks submit when the only unrecorded source sits inside a collapsed group', async () => {
    // The risk this change introduces: 112 rows are now hidden by default, so a staff member sees
    // a tidy screen and could believe coverage is complete. Validation runs on the report, not on
    // what is rendered, regardless of collapse state. Collapsing must never be able to buy a submit.
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    // Every group is collapsed, so no row is on screen at all.
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()

    const submitSpy = vi.spyOn(reportsStore, 'submitReportForQa')
    await userEvent.click(screen.getByRole('button', { name: /submit for qa/i }))

    expect(submitSpy).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent(/mandatory source with no recorded outcome/i)
    expect(screen.queryByText(/ready to submit for qa/i)).not.toBeInTheDocument()
  })

  it('records a source-outcome change via onChange', async () => {
    const report = newDraftReportFixture()
    const onChange = vi.fn()
    render(<BriefBuilderScreen report={report} onChange={onChange} />)

    // Source categories are collapsed by default (see BriefBuilderScreen's grouping) — expand
    // the first one before its select controls exist in the DOM.
    await userEvent.click(screen.getByRole('button', { name: /nz official/i }))
    fireEvent.change(screen.getAllByRole('combobox')[0]!, { target: { value: 'Included' } })

    const latestCall = onChange.mock.calls.at(-1)
    if (!latestCall) throw new Error('onChange was not called')
    expect(latestCall[0].sourceCoverage[0].outcome).toBe('Included')
  })

  it('collapses the 112-source register into category groups by default, with a summary count', () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    expect(screen.getByText('112 mandatory sources — 0 recorded')).toBeInTheDocument()
    // No source rows rendered until a category is expanded — none of the 224 per-row form
    // controls exist in the DOM by default.
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /nz official/i })).toHaveAttribute('aria-expanded', 'false')
  })

  it('expands a single category to reveal only that group\'s source rows', async () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    const nzOfficial = screen.getByRole('button', { name: /nz official/i })
    await userEvent.click(nzOfficial)

    expect(nzOfficial).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('New Zealand Parliament')).toBeInTheDocument()
    // A different, still-collapsed category's sources aren't rendered.
    expect(screen.queryByText('World Trade Organization')).not.toBeInTheDocument()
  })

  it('expands and collapses every category via the Expand all / Collapse all toggle', async () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    await userEvent.click(screen.getByRole('button', { name: /^expand all$/i }))

    expect(screen.getByText('New Zealand Parliament')).toBeInTheDocument()
    expect(screen.getByText('World Trade Organization')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /^collapse all$/i }))

    expect(screen.queryByText('New Zealand Parliament')).not.toBeInTheDocument()
    expect(screen.queryByText('World Trade Organization')).not.toBeInTheDocument()
  })

  it('clears once a candidate is selected and every mandatory source has an outcome', () => {
    render(<ControlledBriefBuilder initial={reportReadyForQa()} />)

    expect(screen.getByText(/ready to submit for qa/i)).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows the reviewer\'s findings when a run comes back for correction', () => {
    const report: DailyBriefReport = {
      ...reportReadyForQa(),
      reportVersion: 'v2',
      qa: {
        reviewer: 'Paras',
        timestamp: '2026-07-30T00:00:00Z',
        result: 'Fail',
        criticalFailuresFound: 'Approved version set present; no uncontrolled change.',
        correctionsRequired: 'See flagged Critical items above.',
      },
      sections: [
        { id: 'sec-1', title: '1. Executive judgement', content: 'x', reviewStatus: 'flagged', flagReason: 'Numbers need a source check' },
      ],
    }
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('v2')
    expect(alert).toHaveTextContent('Paras')
    expect(alert).toHaveTextContent(/approved version set present/i)
    expect(alert).toHaveTextContent(/numbers need a source check/i)
  })

  it('keeps Submit for QA clickable while the brief is invalid, revealing errors instead of submitting', async () => {
    // Not disabled: a disabled button can't be clicked, so there'd be no way to attempt a submit
    // and see why it's blocked. onSubmitForQa still refuses to call the API while errors remain —
    // clicking while invalid must surface the validation box, not silently succeed.
    const submitSpy = vi.spyOn(reportsStore, 'submitReportForQa')
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    const submit = screen.getByRole('button', { name: /submit for qa/i })
    expect(submit).toBeEnabled()
    await userEvent.click(submit)

    expect(submitSpy).not.toHaveBeenCalled()
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent(/at least one scored candidate must be selected/i)
    expect(alert).toHaveTextContent(/mandatory source with no recorded outcome/i)
  })

  it('replaces the calm progress count with the red box once a submit attempt fails', async () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    expect(screen.getByText('0 / 112 sources recorded')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /submit for qa/i }))

    expect(screen.queryByText(/sources recorded/i)).not.toBeInTheDocument()
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('marks a still-blank mandatory Outcome select red once a submit attempt fails', async () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    await userEvent.click(screen.getByRole('button', { name: /nz official/i }))
    const outcomeSelect = screen.getAllByRole('combobox')[0]!
    await userEvent.click(screen.getByRole('button', { name: /submit for qa/i }))

    expect(outcomeSelect.className).toContain('border-inzbc-crimson')
  })

  it('clears a source from the red box and its own red border once its outcome is recorded', async () => {
    render(<ControlledBriefBuilder initial={newDraftReportFixture()} />)

    await userEvent.click(screen.getByRole('button', { name: /nz official/i }))
    const outcomeSelect = screen.getAllByRole('combobox')[0]!
    await userEvent.click(screen.getByRole('button', { name: /submit for qa/i }))
    expect(outcomeSelect.className).toContain('border-inzbc-crimson')
    const alertBefore = screen.getByRole('alert')
    const blankCountBefore = within(alertBefore).getAllByText(/mandatory source with no recorded outcome/i).length

    fireEvent.change(outcomeSelect, { target: { value: 'Included' } })

    expect(outcomeSelect.className).not.toContain('border-inzbc-crimson')
    const alertAfter = screen.getByRole('alert')
    const blankCountAfter = within(alertAfter).getAllByText(/mandatory source with no recorded outcome/i).length
    expect(blankCountAfter).toBe(blankCountBefore - 1)
  })

  it('shows a loading state, then a submitted banner, on a successful submit', async () => {
    render(<ControlledBriefBuilder initial={reportReadyForQa()} />)

    const submit = screen.getByRole('button', { name: /submit for qa/i })
    expect(submit).toBeEnabled()
    await userEvent.click(submit)

    expect(await screen.findByRole('status')).toHaveTextContent(/qa in progress/i)
    expect(screen.queryByRole('button', { name: /submit for qa/i })).not.toBeInTheDocument()
  })

  it('surfaces a submit failure without transitioning the report', async () => {
    vi.spyOn(reportsStore, 'submitReportForQa').mockRejectedValue(new Error('network down'))
    render(<ControlledBriefBuilder initial={reportReadyForQa()} />)

    await userEvent.click(screen.getByRole('button', { name: /submit for qa/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
    // Still the draft form, not a submitted banner — the failed call must not silently advance
    // the run's state.
    expect(screen.getByRole('button', { name: /submit for qa/i })).toBeInTheDocument()
  })
})
