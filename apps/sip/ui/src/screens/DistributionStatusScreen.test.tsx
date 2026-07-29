import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { DailyBriefReport } from '../domain'
import { newDraftReportFixture } from '../lib/fixtures'
import { DistributionStatusScreen } from './DistributionStatusScreen'

describe('DistributionStatusScreen', () => {
  it('is reachable at any run state and renders no write controls', () => {
    render(<DistributionStatusScreen report={newDraftReportFixture()} />)
    expect(screen.getByRole('heading', { level: 2, name: /distribution status/i })).toBeInTheDocument()
    expect(screen.queryAllByRole('button')).toHaveLength(0)
    expect(screen.queryAllByRole('textbox')).toHaveLength(0)
  })

  it('shows the current state and pending status for everything not yet recorded', () => {
    const report = newDraftReportFixture()
    render(<DistributionStatusScreen report={report} />)

    expect(screen.getByText(report.state)).toBeInTheDocument()
    expect(screen.getByText(/qa has not been recorded yet/i)).toBeInTheDocument()
    expect(screen.getByText(/no ceo decision recorded yet/i)).toBeInTheDocument()
    expect(screen.getByText(/no send recorded yet/i)).toBeInTheDocument()
  })

  it('renders a recorded QA result', () => {
    const report: DailyBriefReport = {
      ...newDraftReportFixture(),
      qa: {
        reviewer: 'Paras',
        timestamp: '2026-07-30T02:00:00Z',
        result: 'Pass',
        criticalFailuresFound: '',
        correctionsRequired: '',
      },
    }
    render(<DistributionStatusScreen report={report} />)
    expect(screen.getByText('Pass')).toBeInTheDocument()
    expect(screen.getByText('Paras')).toBeInTheDocument()
  })

  it('shows distribution authorisation as Pending until it has actually been decided', () => {
    const report: DailyBriefReport = {
      ...newDraftReportFixture(),
      decision: {
        reportVersion: 'v0.9 Review Draft',
        decision: 'continue',
        reason: 'On track',
        conditions: '',
        owner: 'Sunil',
        evidenceReference: '',
        nextReviewDate: '2026-08-06',
        decidedAt: '2026-07-30T02:00:00Z',
        distributionAuthorised: null,
        distributionDecidedAt: null,
      },
    }
    render(<DistributionStatusScreen report={report} />)
    expect(screen.getByText(/distribution authorised:/i)).toHaveTextContent('Pending')
  })

  it('renders "No" as a complete, valid distribution outcome, not an error', () => {
    const report: DailyBriefReport = {
      ...newDraftReportFixture(),
      decision: {
        reportVersion: 'v0.9 Review Draft',
        decision: 'continue',
        reason: 'On track',
        conditions: '',
        owner: 'Sunil',
        evidenceReference: '',
        nextReviewDate: '2026-08-06',
        decidedAt: '2026-07-30T02:00:00Z',
        distributionAuthorised: false,
        distributionDecidedAt: '2026-07-30T03:00:00Z',
      },
    }
    render(<DistributionStatusScreen report={report} />)
    expect(screen.getByText(/distribution authorised:/i)).toHaveTextContent('No')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('renders a recorded manual send', () => {
    const report: DailyBriefReport = {
      ...newDraftReportFixture(),
      distribution: {
        sent: true,
        sender: 'Sunil',
        recipient: 'INZBC member distribution list',
        sendTime: '2026-07-30T04:00:00Z',
        channel: 'Email',
        deliveryResult: 'Delivered',
        closeOutStatus: 'Closed, no exceptions',
      },
    }
    render(<DistributionStatusScreen report={report} />)
    expect(screen.getByText('INZBC member distribution list')).toBeInTheDocument()
    expect(screen.getByText('Delivered')).toBeInTheDocument()
  })
})
