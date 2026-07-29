import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as reportsStore from '../api/reportsStore'
import type { DailyBriefReport } from '../domain'
import { generatedDigestContent, newDraftReportFixture } from '../lib/fixtures'
import { CeoDecisionScreen } from './CeoDecisionScreen'

afterEach(() => vi.restoreAllMocks())

function reportAwaitingDecision() {
  return { ...newDraftReportFixture(), ...generatedDigestContent(), state: 'Awaiting CEO Decision' as const }
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

    expect(screen.getByText(report.approvedVersionSet)).toBeInTheDocument()
    expect(
      screen.getByText(/human-reviewed\. not authorised for member, external, website or social publication\./i),
    ).toBeInTheDocument()
    for (const section of generatedDigestContent().sections) {
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
})
