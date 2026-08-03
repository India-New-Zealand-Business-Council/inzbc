import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { NotificationsSection } from './NotificationsSection'

describe('NotificationsSection', () => {
  it('renders placeholder-labelled announcements, not invented real-looking ones', () => {
    render(<NotificationsSection />)
    const placeholders = screen.getAllByText('Placeholder')
    expect(placeholders.length).toBeGreaterThan(0)
    expect(screen.getAllByText(/pending INZBC content/i).length).toBeGreaterThan(0)
  })
})
