import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EventsSection } from './EventsSection'

describe('EventsSection', () => {
  it('renders placeholder-labelled events, not invented real-looking ones', () => {
    render(<EventsSection />)
    const placeholders = screen.getAllByText('Placeholder')
    expect(placeholders.length).toBeGreaterThan(0)
    expect(screen.getAllByText(/pending INZBC event calendar/i).length).toBeGreaterThan(0)
  })

  it('links each Register button out to Member Jungle', () => {
    render(<EventsSection />)
    for (const link of screen.getAllByRole('link', { name: /register/i })) {
      expect(link).toHaveAttribute('href', 'https://inzbc.memberjungle.club')
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    }
  })

  it('links to the full calendar on Member Jungle', () => {
    render(<EventsSection />)
    expect(screen.getByRole('link', { name: /full event calendar/i })).toHaveAttribute(
      'href',
      'https://inzbc.memberjungle.club',
    )
  })
})
