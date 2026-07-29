import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { newDraftReportFixture } from '../lib/fixtures'
import { BriefBuilderScreen } from './BriefBuilderScreen'

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
})
