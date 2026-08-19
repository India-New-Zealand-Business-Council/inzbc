import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ResourcesWidget } from './ResourcesWidget'

describe('ResourcesWidget', () => {
  it('shows each distinct resource category as a shortcut, reused from the full section', () => {
    render(<ResourcesWidget />)

    for (const category of ['FTA sector briefing', 'Trade guide', 'Event recording']) {
      expect(screen.getByRole('link', { name: category })).toHaveAttribute('href', '#resources')
    }
  })

  it('links to the full Resources section', () => {
    render(<ResourcesWidget />)
    expect(screen.getByRole('link', { name: /view all resources/i })).toHaveAttribute(
      'href',
      '#resources',
    )
  })
})
