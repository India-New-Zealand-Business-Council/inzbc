import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as runsClient from './api/runsClient'
import { App } from './App'

afterEach(() => vi.restoreAllMocks())

describe('App', () => {
  it('renders the Executive Dashboard heading and the SIP overview section', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([])
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: /executive dashboard/i })).toBeInTheDocument()
    expect(await screen.findByText('No SIP runs recorded yet.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Coming soon' })).toBeInTheDocument()
  })
})
