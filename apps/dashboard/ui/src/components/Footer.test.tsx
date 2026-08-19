import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Footer } from './Footer'

describe('Footer', () => {
  it('renders the copyright notice and a contact link', () => {
    render(<Footer />)
    expect(screen.getByText(/india new zealand business council/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /contact us/i })).toHaveAttribute(
      'href',
      'mailto:sunil@inzbc.org',
    )
  })

  it('renders the sourced social media links, not Flickr', () => {
    render(<Footer />)
    const social = screen.getByRole('navigation', { name: /social media/i })
    expect(social).toHaveTextContent('X (Twitter)')
    expect(social).toHaveTextContent('LinkedIn')
    expect(social).toHaveTextContent('Facebook')
    expect(social).toHaveTextContent('YouTube')
    expect(social).not.toHaveTextContent('Flickr')

    for (const link of screen.getAllByRole('link', { name: /twitter|linkedin|facebook|youtube/i })) {
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    }
  })
})
