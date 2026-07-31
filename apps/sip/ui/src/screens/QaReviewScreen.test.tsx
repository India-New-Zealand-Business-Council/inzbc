import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as reportsStore from '../api/reportsStore'
import type { DailyBriefReport } from '../domain'
import { candidatesFixture, generatedDigestContent, newDraftReportFixture } from '../lib/fixtures'
import { QaReviewScreen } from './QaReviewScreen'

afterEach(() => vi.restoreAllMocks())

async function answerEveryItem(outcome: 'Pass' | 'N/A' = 'Pass') {
  for (const group of screen.getAllByRole('group')) {
    await userEvent.click(within(group).getByRole('button', { name: outcome }))
  }
}

// All fixture candidates "selected" — this report is already past brief-building in these tests;
// generatedDigestContent derives its Critical/High signals from whatever's passed in (see its
// docstring), so a non-empty selection here keeps "ministerial statement" / "Critical" etc. real.
function reportInQa() {
  return {
    ...newDraftReportFixture(),
    ...generatedDigestContent(candidatesFixture()),
    state: 'QA In Progress' as const,
  }
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
    for (const section of generatedDigestContent(candidatesFixture()).sections) {
      expect(screen.getByText(section.title)).toBeInTheDocument()
      // Multi-line section content (e.g. the executive summary bullets) renders as one text node
      // with embedded newlines, which getByText's default whitespace normalisation won't match
      // verbatim — the first line is enough to confirm the real content rendered.
      expect(screen.getByText(section.content.split('\n')[0]!, { exact: false })).toBeInTheDocument()
    }
  })

  it('renders Critical/High signals with their strength and verification status', () => {
    render(<QaReviewScreen report={reportInQa()} onChange={vi.fn()} />)
    const headline = screen.getByText(/ministerial statement on bilateral trade talks/i)
    expect(headline).toBeInTheDocument()
    // Scoped to this signal's own card: the SIP-188 checklist below has five of its own "Critical"
    // badges (one per Critical item), so an unscoped getByText('Critical') is ambiguous.
    const signalCard = headline.closest('div')!.parentElement!
    expect(within(signalCard).getByText('Critical')).toBeInTheDocument()
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
    expect(initial.sections[0]!.content).toBe(generatedDigestContent(candidatesFixture()).sections[0]!.content)
  })

  it('approves a section, then clears back to pending on a second click', async () => {
    render(<ControlledQaReview initial={reportInQa()} />)
    const approve = screen.getAllByRole('button', { name: 'Approve' })[0]!

    await userEvent.click(approve)
    expect(approve).toHaveAttribute('aria-pressed', 'true')

    await userEvent.click(approve)
    expect(approve).toHaveAttribute('aria-pressed', 'false')
  })

  it('flagging a section reveals a required reason field, and approving clears any flag', async () => {
    render(<ControlledQaReview initial={reportInQa()} />)
    const flag = screen.getAllByRole('button', { name: 'Flag' })[0]!
    const approve = screen.getAllByRole('button', { name: 'Approve' })[0]!

    await userEvent.click(flag)
    expect(flag).toHaveAttribute('aria-pressed', 'true')
    const reasonField = screen.getByLabelText(/reason for flagging/i)
    await userEvent.type(reasonField, 'Numbers need a source check')
    expect(reasonField).toHaveValue('Numbers need a source check')

    await userEvent.click(approve)
    expect(flag).toHaveAttribute('aria-pressed', 'false')
    expect(screen.queryByLabelText(/reason for flagging/i)).not.toBeInTheDocument()
  })

  it('flagging and approving are mutually exclusive on the same section', async () => {
    render(<ControlledQaReview initial={reportInQa()} />)
    const approve = screen.getAllByRole('button', { name: 'Approve' })[0]!
    const flag = screen.getAllByRole('button', { name: 'Flag' })[0]!

    await userEvent.click(approve)
    expect(approve).toHaveAttribute('aria-pressed', 'true')

    await userEvent.click(flag)
    expect(flag).toHaveAttribute('aria-pressed', 'true')
    expect(approve).toHaveAttribute('aria-pressed', 'false')
  })

  it('shows a running checklist pass rate as items are answered', async () => {
    render(<ControlledQaReview initial={reportInQa()} />)
    expect(screen.getByText(/checklist pass rate/i)).toHaveTextContent('0%')

    await userEvent.click(within(screen.getAllByRole('group')[0]!).getByRole('button', { name: 'Pass' }))
    expect(screen.getByText(/checklist pass rate/i)).toHaveTextContent('100%')
  })

  it('disables Record QA result until every checklist item is answered', () => {
    render(<QaReviewScreen report={reportInQa()} onChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: /record qa result/i })).toBeDisabled()
    expect(screen.getByText(/still need pass\/fail\/n\/a/i)).toBeInTheDocument()
  })

  it('records a clean pass and advances the report past this screen toward the CEO decision screen', async () => {
    render(<ControlledQaReview initial={reportInQa()} />)
    await answerEveryItem('Pass')

    await userEvent.click(screen.getByRole('button', { name: /record qa result/i }))
    expect(await screen.findByRole('status')).toHaveTextContent(/awaiting ceo decision/i)
  })

  it('a Critical failure visibly blocks the clean-pass path before submission, not only after', async () => {
    render(<ControlledQaReview initial={reportInQa()} />)
    await answerEveryItem('Pass')
    const criticalGroup = screen.getByRole('group', { name: /approved version set present/i })
    await userEvent.click(within(criticalGroup).getByRole('button', { name: 'Fail' }))

    // docs/sip-ui-spec.md: "Any Critical failure disables 'Submit to CEO' entirely" — must be
    // visible before the click, not just a different outcome revealed after an identical-looking
    // button is submitted. Plain "Record QA result" is gone the moment the Critical item reads
    // Fail, replaced by a crimson button naming the correction outcome.
    expect(screen.queryByRole('button', { name: /^record qa result$/i })).not.toBeInTheDocument()
    const recordButton = screen.getByRole('button', { name: /record critical fail/i })
    expect(recordButton.className).toMatch(/bg-inzbc-crimson/)

    await userEvent.click(recordButton)

    expect(await screen.findByRole('button', { name: /send back for correction/i })).toBeInTheDocument()
    expect(screen.getByText(/last recorded result:/i)).toHaveTextContent('Fail')
    // The spec is explicit there is no override for a Critical fail — confirm the pass action is
    // simply gone, not just relabelled.
    expect(screen.queryByRole('button', { name: /record qa result|record critical fail/i })).not.toBeInTheDocument()
  })

  it('sending back for correction returns the run to Report Drafted, out of this screen\'s reach', async () => {
    const failed: DailyBriefReport = {
      ...reportInQa(),
      state: 'QA Failed',
      qa: { reviewer: 'Paras', timestamp: '2026-07-30T00:00:00Z', result: 'Fail', criticalFailuresFound: 'x', correctionsRequired: 'y' },
    }
    render(<ControlledQaReview initial={failed} />)

    await userEvent.click(screen.getByRole('button', { name: /send back for correction/i }))
    expect(await screen.findByRole('status')).toHaveTextContent(/report drafted/i)
  })

  it('surfaces a record-result failure without transitioning the report', async () => {
    vi.spyOn(reportsStore, 'submitQaResult').mockRejectedValue(new Error('network down'))
    render(<ControlledQaReview initial={reportInQa()} />)
    await answerEveryItem('Pass')

    await userEvent.click(screen.getByRole('button', { name: /record qa result/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
    expect(screen.getByRole('button', { name: /record qa result/i })).toBeInTheDocument()
  })

  it('gives the Edit/Done toggle a real touch target, not a bare underlined glyph', () => {
    render(<QaReviewScreen report={reportInQa()} onChange={vi.fn()} />)
    const editButton = screen.getAllByRole('button', { name: 'Edit' })[0]!
    expect(editButton.className).toMatch(/min-h-11/)
  })

  it('wraps the Critical/High signal header instead of forcing a long headline to overflow', () => {
    render(<QaReviewScreen report={reportInQa()} onChange={vi.fn()} />)
    const heading = screen.getByText(/ministerial statement on bilateral trade talks/i)
    expect(heading.parentElement?.className).toMatch(/flex-wrap/)
  })
})
