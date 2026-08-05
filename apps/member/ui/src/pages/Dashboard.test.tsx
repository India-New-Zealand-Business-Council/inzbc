import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Dashboard } from './Dashboard'

describe('Dashboard', () => {
  it('renders the overview heading', () => {
    render(<Dashboard />)
    expect(screen.getByRole('heading', { level: 2, name: /overview/i })).toBeInTheDocument()
  })

  it('renders all four summary widgets as distinct labelled groups', () => {
    render(<Dashboard />)
    for (const name of ['Notifications', 'Membership', 'Upcoming Events', 'Resources']) {
      expect(screen.getByRole('group', { name })).toBeInTheDocument()
    }
  })

  it('lays out the widgets in a grid that collapses to one column on mobile', () => {
    // 1 column by default (mobile), 2 at sm, 4 at lg — see the class comment in Dashboard.tsx.
    // jsdom doesn't evaluate media queries, so this asserts the classes are present rather than
    // measured layout; the breakpoint behavior itself is standard Tailwind, not custom logic.
    render(<Dashboard />)
    const notifications = screen.getByRole('group', { name: 'Notifications' })
    const grid = notifications.parentElement
    expect(grid).toHaveClass('grid', 'grid-cols-1', 'sm:grid-cols-2', 'lg:grid-cols-4')
  })

  it('orders widgets to match the full sections below: Notifications, Membership, Events, Resources', () => {
    render(<Dashboard />)
    const groups = screen.getAllByRole('group').map((group) => group.getAttribute('aria-labelledby'))
    const names = groups.map((id) => document.getElementById(id!)?.textContent)
    expect(names).toEqual(['Notifications', 'Membership', 'Upcoming Events', 'Resources'])
  })
})
