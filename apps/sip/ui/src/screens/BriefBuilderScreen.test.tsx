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

  it('blocks on blank mandatory source outcomes and no candidate selected, by default', () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent(/at least one scored candidate must be selected/i)
    expect(alert).toHaveTextContent(/mandatory source with no recorded outcome/i)
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

  it('disables Submit for QA while the brief is invalid', () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: /submit for qa/i })).toBeDisabled()
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
