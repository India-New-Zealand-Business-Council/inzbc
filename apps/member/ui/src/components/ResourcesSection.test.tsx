import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ResourcesSection } from './ResourcesSection'

describe('ResourcesSection', () => {
  it('renders placeholder-labelled resources, not invented real-looking ones', () => {
    render(<ResourcesSection />)
    const placeholders = screen.getAllByText('Placeholder')
    expect(placeholders.length).toBeGreaterThan(0)
    expect(screen.getAllByText(/pending INZBC resource library/i).length).toBeGreaterThan(0)
  })

  it('links each item out to Member Jungle rather than hosting a download', () => {
    render(<ResourcesSection />)
    for (const link of screen.getAllByRole('link', { name: /sign in to view/i })) {
      expect(link).toHaveAttribute('href', 'https://inzbc.memberjungle.club')
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    }
  })
})
