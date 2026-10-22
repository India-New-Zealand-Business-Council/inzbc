import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as dashboardClient from './api/dashboardClient'
import { App } from './App'

afterEach(() => vi.restoreAllMocks())

describe('App', () => {
  it('renders the Executive Dashboard heading and the executive overview section', async () => {
    vi.spyOn(dashboardClient, 'getDashboard').mockResolvedValue({
      run: null,
      gates: { qa_status: null, report_approval: null, distribution_authority: null, distribution_recipient: null },
      coverage: { total: 0, included: 0, by_verification: {} },
      open_actions: [],
      open_actions_truncated: false,
    })
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: /executive dashboard/i })).toBeInTheDocument()
    expect(await screen.findByText('No SIP runs recorded yet.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Coming soon' })).toBeInTheDocument()
  })
})
