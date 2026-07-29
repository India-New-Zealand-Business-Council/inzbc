import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { generatedDigestContent, newDraftReportFixture } from '../lib/fixtures'
import { QaReviewScreen } from './QaReviewScreen'

function reportInQa() {
  return { ...newDraftReportFixture(), ...generatedDigestContent(), state: 'QA In Progress' as const }
}

describe('QaReviewScreen', () => {
  it('is not reachable before the run enters QA In Progress', () => {
    render(<QaReviewScreen report={newDraftReportFixture()} />)
    expect(screen.getByRole('status')).toHaveTextContent(/not reachable yet/i)
    expect(screen.queryByText(/digest content for review/i)).not.toBeInTheDocument()
  })

  it('blocks the screen when the reviewer is also the analyst', () => {
    const report = { ...reportInQa(), analyst: 'Paras', reviewer: 'Paras' }
    render(<QaReviewScreen report={report} />)
    expect(screen.getByRole('alert')).toHaveTextContent(/cannot be its own reviewer/i)
  })

  it('renders every brief section read-only once QA is reachable', () => {
    render(<QaReviewScreen report={reportInQa()} />)
    for (const section of generatedDigestContent().sections) {
      expect(screen.getByText(section.title)).toBeInTheDocument()
      // Multi-line section content (e.g. the executive summary bullets) renders as one text node
      // with embedded newlines, which getByText's default whitespace normalisation won't match
      // verbatim — the first line is enough to confirm the real content rendered.
      expect(screen.getByText(section.content.split('\n')[0]!, { exact: false })).toBeInTheDocument()
    }
  })

  it('renders Critical/High signals with their strength and verification status', () => {
    render(<QaReviewScreen report={reportInQa()} />)
    expect(screen.getByText(/ministerial statement on bilateral trade talks/i)).toBeInTheDocument()
    expect(screen.getByText('Critical')).toBeInTheDocument()
    expect(screen.getAllByText(/verification: verified/i)).toHaveLength(2)
  })

  it('shows a QA Failed banner when returned for correction', () => {
    const report = { ...reportInQa(), state: 'QA Failed' as const }
    render(<QaReviewScreen report={report} />)
    expect(screen.getByText(/failed qa and has been returned for correction/i)).toBeInTheDocument()
  })
})
