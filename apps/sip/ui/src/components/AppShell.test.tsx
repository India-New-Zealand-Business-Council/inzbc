import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { AppShell } from './AppShell'

describe('AppShell', () => {
  it('shows the Brief Builder screen by default', () => {
    render(<AppShell />)
    expect(screen.getByRole('heading', { level: 2, name: /brief builder/i })).toBeInTheDocument()
  })

  it('switches screens via the nav, marking the active tab with aria-current', async () => {
    render(<AppShell />)
    const qaTab = screen.getByRole('button', { name: 'QA Review' })
    expect(qaTab).not.toHaveAttribute('aria-current')

    await userEvent.click(qaTab)

    expect(screen.getByRole('heading', { level: 2, name: /qa review/i })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 2, name: /brief builder/i })).not.toBeInTheDocument()
    expect(qaTab).toHaveAttribute('aria-current', 'page')
  })

  it('reaches all four screens', async () => {
    render(<AppShell />)
    await userEvent.click(screen.getByRole('button', { name: 'CEO Decision' }))
    expect(screen.getByRole('heading', { level: 2, name: /ceo decision/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Distribution Status' }))
    expect(screen.getByRole('heading', { level: 2, name: /distribution status/i })).toBeInTheDocument()
  })
})
