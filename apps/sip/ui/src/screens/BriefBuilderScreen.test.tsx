import { fireEvent, render, screen } from '@testing-library/react'
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

describe('BriefBuilderScreen', () => {
  it('renders the run header as read-only data, not editable inputs', () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    expect(screen.getByText(report.runId)).toBeInTheDocument()
    expect(screen.getByText(report.analyst)).toBeInTheDocument()
    expect(screen.queryByLabelText(/run id/i)).not.toBeInTheDocument()
  })

  it('reports a coverage-window edit via onChange without mutating the caller-owned report', async () => {
    const report = newDraftReportFixture()
    const onChange = vi.fn()
    render(<BriefBuilderScreen report={report} onChange={onChange} />)

    fireEvent.change(screen.getByLabelText(/coverage window start/i), { target: { value: '2026-08-01' } })

    expect(onChange).toHaveBeenCalled()
    const latestCall = onChange.mock.calls.at(-1)
    if (!latestCall) throw new Error('onChange was not called')
    expect(latestCall[0].coverageStart).toBe('2026-08-01')
    expect(report.coverageStart).not.toBe('2026-08-01')
  })

  it('lists fixture candidates for source selection and tracks the count selected', async () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    expect(screen.getByText('0 candidate(s) selected')).toBeInTheDocument()
    const checkboxes = screen.getAllByRole('checkbox')
    await userEvent.click(checkboxes[0]!)

    expect(screen.getByText('1 candidate(s) selected')).toBeInTheDocument()
  })

  it('labels the focus note as non-canonical rather than presenting it as a SIP-186 field', () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)
    expect(screen.getByText(/not a sip-186 field/i)).toBeInTheDocument()
  })

  it('blocks on blank mandatory source outcomes and no candidate selected, by default', () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent(/at least one scored candidate must be selected/i)
    expect(alert).toHaveTextContent(/mandatory source with no recorded outcome/i)
    expect(screen.queryByText(/ready to submit for qa/i)).not.toBeInTheDocument()
  })

  it('clears once a candidate is selected and every mandatory source has an outcome', async () => {
    render(<ControlledBriefBuilder initial={newDraftReportFixture()} />)

    await userEvent.click(screen.getAllByRole('checkbox')[0]!)
    for (const select of screen.getAllByRole('combobox')) {
      fireEvent.change(select, { target: { value: 'Included' } })
    }

    expect(screen.getByText(/ready to submit for qa/i)).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('disables Submit for QA while the brief is invalid', () => {
    const report = newDraftReportFixture()
    render(<BriefBuilderScreen report={report} onChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: /submit for qa/i })).toBeDisabled()
  })

  async function fillValidBrief() {
    render(<ControlledBriefBuilder initial={newDraftReportFixture()} />)
    await userEvent.click(screen.getAllByRole('checkbox')[0]!)
    for (const select of screen.getAllByRole('combobox')) {
      fireEvent.change(select, { target: { value: 'Included' } })
    }
  }

  it('shows a loading state, then a submitted banner, on a successful submit', async () => {
    await fillValidBrief()

    const submit = screen.getByRole('button', { name: /submit for qa/i })
    expect(submit).toBeEnabled()
    await userEvent.click(submit)

    expect(await screen.findByRole('status')).toHaveTextContent(/qa in progress/i)
    expect(screen.queryByRole('button', { name: /submit for qa/i })).not.toBeInTheDocument()
  })

  it('surfaces a submit failure without transitioning the report', async () => {
    vi.spyOn(reportsStore, 'submitReportForQa').mockRejectedValue(new Error('network down'))
    await fillValidBrief()

    await userEvent.click(screen.getByRole('button', { name: /submit for qa/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
    // Still the draft form, not a submitted banner — the failed call must not silently advance
    // the run's state.
    expect(screen.getByRole('button', { name: /submit for qa/i })).toBeInTheDocument()
  })
})
