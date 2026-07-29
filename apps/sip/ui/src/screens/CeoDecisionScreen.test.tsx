import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { generatedDigestContent, newDraftReportFixture } from '../lib/fixtures'
import { CeoDecisionScreen } from './CeoDecisionScreen'

function reportAwaitingDecision() {
  return { ...newDraftReportFixture(), ...generatedDigestContent(), state: 'Awaiting CEO Decision' as const }
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
})
