import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EventsWidget } from './EventsWidget'

describe('EventsWidget', () => {
  it('shows placeholder-labelled events reused from the full section', () => {
    render(<EventsWidget />)
    expect(screen.getAllByText('Placeholder')).toHaveLength(2)
    expect(screen.getAllByText(/pending INZBC event calendar/i).length).toBeGreaterThan(0)
  })

  it('links to the full Events section and directly to the Member Jungle calendar', () => {
    render(<EventsWidget />)
    expect(screen.getByRole('link', { name: /view all events/i })).toHaveAttribute('href', '#events')
    expect(screen.getByRole('link', { name: /full calendar on member jungle/i })).toHaveAttribute(
      'href',
      'https://inzbc.memberjungle.club',
    )
  })
})
