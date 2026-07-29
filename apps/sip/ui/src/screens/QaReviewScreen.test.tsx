import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import type { DailyBriefReport } from '../domain'
import { generatedDigestContent, newDraftReportFixture } from '../lib/fixtures'
import { QaReviewScreen } from './QaReviewScreen'

function reportInQa() {
  return { ...newDraftReportFixture(), ...generatedDigestContent(), state: 'QA In Progress' as const }
}

/** A controlled wrapper so edit tests exercise real state updates, not a static prop. */
function ControlledQaReview({ initial }: { initial: DailyBriefReport }) {
  const [report, setReport] = useState(initial)
  return <QaReviewScreen report={report} onChange={setReport} />
}

describe('QaReviewScreen', () => {
  it('is not reachable before the run enters QA In Progress', () => {
    render(<QaReviewScreen report={newDraftReportFixture()} onChange={vi.fn()} />)
    expect(screen.getByRole('status')).toHaveTextContent(/not reachable yet/i)
    expect(screen.queryByText(/digest content for review/i)).not.toBeInTheDocument()
  })

  it('blocks the screen when the reviewer is also the analyst', () => {
    const report = { ...reportInQa(), analyst: 'Paras', reviewer: 'Paras' }
    render(<QaReviewScreen report={report} onChange={vi.fn()} />)
    expect(screen.getByRole('alert')).toHaveTextContent(/cannot be its own reviewer/i)
  })

  it('renders every brief section read-only once QA is reachable', () => {
    render(<QaReviewScreen report={reportInQa()} onChange={vi.fn()} />)
    for (const section of generatedDigestContent().sections) {
      expect(screen.getByText(section.title)).toBeInTheDocument()
      // Multi-line section content (e.g. the executive summary bullets) renders as one text node
      // with embedded newlines, which getByText's default whitespace normalisation won't match
      // verbatim — the first line is enough to confirm the real content rendered.
      expect(screen.getByText(section.content.split('\n')[0]!, { exact: false })).toBeInTheDocument()
    }
  })

  it('renders Critical/High signals with their strength and verification status', () => {
    render(<QaReviewScreen report={reportInQa()} onChange={vi.fn()} />)
    expect(screen.getByText(/ministerial statement on bilateral trade talks/i)).toBeInTheDocument()
    expect(screen.getByText('Critical')).toBeInTheDocument()
    expect(screen.getAllByText(/verification: verified/i)).toHaveLength(2)
  })

  it('shows a QA Failed banner when returned for correction', () => {
    const report = { ...reportInQa(), state: 'QA Failed' as const }
    render(<QaReviewScreen report={report} onChange={vi.fn()} />)
    expect(screen.getByText(/failed qa and has been returned for correction/i)).toBeInTheDocument()
  })

  it('sections are read-only until Edit is clicked, one section at a time', async () => {
    render(<ControlledQaReview initial={reportInQa()} />)
    const editButtons = screen.getAllByRole('button', { name: 'Edit' })
    expect(screen.queryAllByRole('textbox')).toHaveLength(0)

    await userEvent.click(editButtons[0]!)
    expect(screen.getAllByRole('textbox')).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'Done' })).toBeInTheDocument()

    // Opening a second section's editor doesn't leave the first one open too.
    const stillEditButtons = screen.getAllByRole('button', { name: 'Edit' })
    await userEvent.click(stillEditButtons[0]!)
    expect(screen.getAllByRole('textbox')).toHaveLength(1)
  })

  it('edits section content in place and reports the change via onChange', async () => {
    render(<ControlledQaReview initial={reportInQa()} />)
    await userEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0]!)

    const textarea = screen.getByRole('textbox')
    await userEvent.clear(textarea)
    await userEvent.type(textarea, 'Corrected section text')

    expect(screen.getByDisplayValue('Corrected section text')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Done' }))
    expect(screen.getByText('Corrected section text')).toBeInTheDocument()
    expect(screen.queryAllByRole('textbox')).toHaveLength(0)
  })

  it('does not mutate the caller-owned report object when editing', async () => {
    const initial = reportInQa()
    const onChange = vi.fn()
    render(<QaReviewScreen report={initial} onChange={onChange} />)

    await userEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0]!)
    await userEvent.type(screen.getByRole('textbox'), 'x')

    expect(onChange).toHaveBeenCalled()
    expect(initial.sections[0]!.content).toBe(generatedDigestContent().sections[0]!.content)
  })
})
