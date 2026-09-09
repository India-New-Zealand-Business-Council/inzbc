import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { AppShell } from './AppShell'

describe('AppShell', () => {
  it('opens on the platform overview', async () => {
    // Was Brief Builder, when this shell was one tool. With four modules behind it, landing on
    // any single module's first screen hides the other three.
    render(<AppShell />)
    expect(screen.getByRole('heading', { level: 1, name: /inzbc platform/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Brief Builder' }))
    expect(screen.getByRole('heading', { level: 1, name: /brief builder/i })).toBeInTheDocument()
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

  it('reaches every module from the one nav', async () => {
    // The whole point of the shell: one running app, not five. If a tab stops resolving to its
    // module this fails, which is what a demo depends on.
    render(<AppShell />)

    await userEvent.click(screen.getByRole('button', { name: 'CEO Decision' }))
    expect(screen.getByRole('heading', { level: 1, name: /ceo decision/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Distribution' }))
    expect(screen.getByRole('heading', { level: 1, name: /distribution/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'FTA Explainer' }))
    expect(screen.getByRole('heading', { level: 1, name: /fta explainer/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Comms Assistant' }))
    expect(screen.getByRole('heading', { level: 1, name: /comms assistant/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Member Portal' }))
    expect(screen.getByRole('heading', { level: 1, name: /member portal/i })).toBeInTheDocument()
  })
})
