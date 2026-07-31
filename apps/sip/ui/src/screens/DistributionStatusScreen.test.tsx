import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { DailyBriefReport } from '../domain'
import { archiveFixture, newDraftReportFixture } from '../lib/fixtures'
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

    // Scoped via the "Current state" <dt>, not a bare getByText(report.state): the run archive
    // below can contain a fixture row in the same state ("Report Drafted"), which would otherwise
    // make this an ambiguous, multiple-element match.
    const currentStateDt = screen.getByText('Current state')
    expect(currentStateDt.nextElementSibling).toHaveTextContent(report.state)
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
    // Scoped to the QA result card, and matched as a substring: the archive fixture below has its
    // own "Pass" rows, and "Paras" only ever renders as "Reviewer: Paras" — an exact, unscoped
    // getByText('Pass') / getByText('Paras') matches neither correctly.
    const qaSection = screen.getByText('QA result').closest('div')!
    expect(within(qaSection).getByText('Pass', { exact: false })).toBeInTheDocument()
    expect(within(qaSection).getByText(/paras/i)).toBeInTheDocument()
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
    // { exact: false }: both render as one text node with their label ("Recipient: ...",
    // "Delivery result: ..."), so an exact match finds neither.
    expect(screen.getByText('INZBC member distribution list', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('Delivered', { exact: false })).toBeInTheDocument()
  })

  it('renders the run archive as a read-only table, one row per past run', () => {
    render(<DistributionStatusScreen report={newDraftReportFixture()} />)
    const table = screen.getByRole('table')
    const rows = within(table).getAllByRole('row')
    // Header row + one row per fixture run.
    expect(rows).toHaveLength(archiveFixture().length + 1)

    const firstRun = archiveFixture()[0]!
    expect(within(table).getByText(firstRun.runId)).toBeInTheDocument()
    expect(within(table).getByText(firstRun.reportDate)).toBeInTheDocument()
  })

  it('shows Pending in the archive for a run with no QA/decision/distribution recorded yet', () => {
    render(<DistributionStatusScreen report={newDraftReportFixture()} />)
    const undecidedRun = archiveFixture().find((run) => run.decision === null)!
    const row = screen.getByText(undecidedRun.runId).closest('tr')
    expect(row).not.toBeNull()
    expect(within(row!).getAllByText('Pending').length).toBeGreaterThan(0)
  })
})
