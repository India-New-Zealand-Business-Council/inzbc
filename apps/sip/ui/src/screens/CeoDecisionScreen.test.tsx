import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as reportsStore from '../api/reportsStore'
import { stubReportsFetch } from '../api/reportsStore.testSupport'
import type { DailyBriefReport } from '../domain'
import { candidatesFixture, generatedDigestContent, newDraftReportFixture } from '../lib/fixtures'
import { CeoDecisionScreen } from './CeoDecisionScreen'

beforeEach(() => stubReportsFetch())
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

// All fixture candidates "selected" — this report is already past brief-building in these tests,
// so the exact selection doesn't matter here, only that generatedDigestContent gets a non-empty
// one (see its docstring: signals now come from the selection, not a hardcoded pair).
function reportAwaitingDecision() {
  return {
    ...newDraftReportFixture(),
    ...generatedDigestContent(candidatesFixture()),
    state: 'Awaiting CEO Decision' as const,
    reportVersionId: 'rv-1',
  }
}

/** A controlled wrapper so submit tests exercise real state updates, not a static prop. */
function ControlledCeoDecision({ initial }: { initial: DailyBriefReport }) {
  const [report, setReport] = useState(initial)
  return <CeoDecisionScreen report={report} onChange={setReport} />
}

async function fillRequiredFields() {
  await userEvent.type(screen.getByLabelText(/^reason$/i), 'On track, no concerns')
  await userEvent.type(screen.getByLabelText(/owner/i), 'Sunil')
  await userEvent.type(screen.getByLabelText(/evidence reference/i), 'Doc ref 123')
  fireEvent.change(screen.getByLabelText(/next review date/i), { target: { value: '2026-08-06' } })
}

describe('CeoDecisionScreen', () => {
  it('is not reachable before QA has passed', () => {
    render(<CeoDecisionScreen report={newDraftReportFixture()} onChange={vi.fn()} />)
    expect(screen.getByRole('status')).toHaveTextContent(/not reachable yet/i)
    expect(screen.queryByText(/digest preview/i)).not.toBeInTheDocument()
  })

  it('renders the digest preview, governance line, and the version being decided', () => {
    const report = reportAwaitingDecision()
    render(<CeoDecisionScreen report={report} onChange={vi.fn()} />)

    // getByText(..., { exact: false }) on a short string like "v1" can match this paragraph *and*
    // its parent (whose combined text also contains it) — toHaveTextContent on the one paragraph
    // avoids that ambiguity.
    const versionLine = screen.getByText(/deciding against report version/i)
    expect(versionLine).toHaveTextContent(report.reportVersion)
    expect(versionLine).toHaveTextContent(report.approvedVersionSet)
    expect(
      screen.getByText(/human-reviewed\. not authorised for member, external, website or social publication\./i),
    ).toBeInTheDocument()
    for (const section of generatedDigestContent(candidatesFixture()).sections) {
      expect(screen.getByText(section.title)).toBeInTheDocument()
    }
  })

  it('renders the CEO action list', () => {
    render(<CeoDecisionScreen report={reportAwaitingDecision()} onChange={vi.fn()} />)
    expect(screen.getByText(/placeholder ceo action item/i)).toBeInTheDocument()
    expect(screen.getByText(/owner: \[fixture\] owner tbd/i)).toBeInTheDocument()
  })

  it('offers exactly one selected report decision at a time, never two combined', async () => {
    render(<CeoDecisionScreen report={reportAwaitingDecision()} onChange={vi.fn()} />)
    const group = screen.getByRole('radiogroup', { name: /report decision/i })
    expect(group).toBeInTheDocument()

    const continueOption = screen.getByRole('radio', { name: 'Continue' })
    const pauseOption = screen.getByRole('radio', { name: 'Pause' })
    expect(continueOption).toHaveAttribute('aria-checked', 'false')

    await userEvent.click(continueOption)
    expect(continueOption).toHaveAttribute('aria-checked', 'true')
    expect(pauseOption).toHaveAttribute('aria-checked', 'false')

    await userEvent.click(pauseOption)
    expect(pauseOption).toHaveAttribute('aria-checked', 'true')
    expect(continueOption).toHaveAttribute('aria-checked', 'false')
  })

  it('does not offer the decision picker once a decision state has already been reached', () => {
    const report = { ...reportAwaitingDecision(), state: 'Continue' as const }
    render(<CeoDecisionScreen report={report} onChange={vi.fn()} />)
    expect(screen.queryByRole('radiogroup')).not.toBeInTheDocument()
    expect(screen.getByText(/report decision already recorded/i)).toBeInTheDocument()
  })

  it('shows the required-fields form only once a decision type is picked', async () => {
    render(<CeoDecisionScreen report={reportAwaitingDecision()} onChange={vi.fn()} />)
    expect(screen.queryByLabelText(/^reason$/i)).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('radio', { name: 'Continue' }))
    expect(screen.getByLabelText(/^reason$/i)).toBeInTheDocument()
  })

  it('disables Record decision until reason, owner, evidence reference and next review date are filled', async () => {
    render(<CeoDecisionScreen report={reportAwaitingDecision()} onChange={vi.fn()} />)
    await userEvent.click(screen.getByRole('radio', { name: 'Continue' }))

    expect(screen.getByRole('button', { name: /record decision/i })).toBeDisabled()
    expect(screen.getByRole('alert')).toHaveTextContent(/still required/i)

    await fillRequiredFields()
    expect(screen.getByRole('button', { name: /record decision/i })).toBeEnabled()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('conditions is optional — omitting it does not block submission', async () => {
    render(<CeoDecisionScreen report={reportAwaitingDecision()} onChange={vi.fn()} />)
    await userEvent.click(screen.getByRole('radio', { name: 'Continue' }))
    await fillRequiredFields()
    expect(screen.getByLabelText(/conditions/i)).toHaveValue('')
    expect(screen.getByRole('button', { name: /record decision/i })).toBeEnabled()
  })

  it('records a Continue decision, leaving distribution unauthorised and undecided', async () => {
    render(<ControlledCeoDecision initial={reportAwaitingDecision()} />)
    await userEvent.click(screen.getByRole('radio', { name: 'Continue' }))
    await fillRequiredFields()

    await userEvent.click(screen.getByRole('button', { name: /record decision/i }))

    expect(await screen.findByText(/report decision already recorded/i)).toHaveTextContent('continue')
  })

  it('records a Stop decision, ending the run under this Run ID', async () => {
    render(<ControlledCeoDecision initial={reportAwaitingDecision()} />)
    await userEvent.click(screen.getByRole('radio', { name: 'Stop' }))
    await fillRequiredFields()

    await userEvent.click(screen.getByRole('button', { name: /record decision/i }))

    expect(await screen.findByText(/report decision already recorded/i)).toHaveTextContent('stop')
  })

  it('surfaces a record-decision failure without transitioning the report', async () => {
    vi.spyOn(reportsStore, 'recordCeoDecision').mockRejectedValue(new Error('network down'))
    render(<ControlledCeoDecision initial={reportAwaitingDecision()} />)
    await userEvent.click(screen.getByRole('radio', { name: 'Continue' }))
    await fillRequiredFields()

    await userEvent.click(screen.getByRole('button', { name: /record decision/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
    expect(screen.getByRole('button', { name: /record decision/i })).toBeInTheDocument()
  })

  function reportDecided(state: 'Continue' | 'Continue With Correction' | 'Paused' | 'Stopped'): DailyBriefReport {
    return {
      ...reportAwaitingDecision(),
      state,
      decision: {
        reportVersion: 'v0.9 Review Draft',
        decision: 'continue' as const,
        reason: 'On track',
        conditions: '',
        owner: 'Sunil',
        evidenceReference: 'Doc ref',
        nextReviewDate: '2026-08-06',
        decidedAt: '2026-07-30T00:00:00Z',
        distributionAuthorised: null,
        distributionDecidedAt: null,
      },
    }
  }

  it('offers distribution authorisation once a decision reaches Continue', () => {
    render(<CeoDecisionScreen report={reportDecided('Continue')} onChange={vi.fn()} />)
    expect(screen.getByRole('heading', { name: /authorise distribution/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /yes, authorise/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'No' })).toBeInTheDocument()
  })

  it('does not offer distribution authorisation for a Paused or Stopped run', () => {
    render(<CeoDecisionScreen report={reportDecided('Paused')} onChange={vi.fn()} />)
    expect(screen.queryByRole('heading', { name: /authorise distribution/i })).not.toBeInTheDocument()
  })

  it('does not re-offer distribution authorisation once it has already been decided', () => {
    const report = reportDecided('Continue')
    if (!report.decision) throw new Error('expected reportDecided to set a decision')
    report.decision = { ...report.decision, distributionAuthorised: true, distributionDecidedAt: '2026-07-30T01:00:00Z' }
    render(<CeoDecisionScreen report={report} onChange={vi.fn()} />)
    expect(screen.queryByRole('heading', { name: /authorise distribution/i })).not.toBeInTheDocument()
    expect(screen.getByText(/distribution authorised:/i)).toHaveTextContent('Yes')
  })

  it('gates "Yes" behind a confirmation modal that does not fire until confirmed', async () => {
    render(<ControlledCeoDecision initial={reportDecided('Continue')} />)
    await userEvent.click(screen.getByRole('button', { name: /yes, authorise/i }))

    const dialog = screen.getByRole('dialog', { name: /authorise distribution/i })
    expect(dialog).toBeInTheDocument()
    expect(screen.queryByText(/distribution authorised: yes/i)).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.queryByText(/distribution authorised:/i)).not.toBeInTheDocument()
  })

  it('names the authorised recipient and confirms automated channels are off, in the modal', async () => {
    render(<ControlledCeoDecision initial={reportDecided('Continue')} />)
    await userEvent.click(screen.getByRole('button', { name: /yes, authorise/i }))

    const dialog = screen.getByRole('dialog', { name: /authorise distribution/i })
    expect(dialog).toHaveTextContent(/sunilkaushalnz@gmail\.com/i)
    expect(dialog).toHaveTextContent(/all disabled/i)
  })

  it('confirming the modal authorises distribution and advances to Approved for Manual Distribution', async () => {
    render(<ControlledCeoDecision initial={reportDecided('Continue')} />)
    await userEvent.click(screen.getByRole('button', { name: /yes, authorise/i }))
    await userEvent.click(screen.getByRole('button', { name: /confirm authorisation/i }))

    expect(await screen.findByText(/distribution authorised:/i)).toHaveTextContent('Yes')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('"No" does not open a modal and records a valid, complete decline', async () => {
    render(<ControlledCeoDecision initial={reportDecided('Continue')} />)
    await userEvent.click(screen.getByRole('button', { name: 'No' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(await screen.findByText(/distribution authorised:/i)).toHaveTextContent('No')
  })

  it('surfaces a distribution-authorisation failure without transitioning the report', async () => {
    vi.spyOn(reportsStore, 'authoriseDistribution').mockRejectedValue(new Error('network down'))
    render(<ControlledCeoDecision initial={reportDecided('Continue')} />)
    await userEvent.click(screen.getByRole('button', { name: 'No' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
    expect(screen.queryByText(/distribution authorised:/i)).not.toBeInTheDocument()
  })
})
