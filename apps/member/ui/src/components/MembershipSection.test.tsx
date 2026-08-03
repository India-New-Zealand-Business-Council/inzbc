import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MembershipSection } from './MembershipSection'

describe('MembershipSection', () => {
  it('renders Join/Renew, Directory and Billing actions', () => {
    render(<MembershipSection />)
    expect(screen.getByText('Join / Renew')).toBeInTheDocument()
    expect(screen.getByText('Member Directory')).toBeInTheDocument()
    expect(screen.getByText('Billing & Invoices')).toBeInTheDocument()
  })

  it('links every action out to Member Jungle rather than handling it in-portal', () => {
    render(<MembershipSection />)
    const links = screen.getAllByRole('link', { name: /continue on member jungle/i })
    expect(links).toHaveLength(3)
    for (const link of links) {
      expect(link).toHaveAttribute('href', 'https://inzbc.memberjungle.club')
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    }
  })

  it('does not use the Lavender focus ring on the tangerine buttons', () => {
    // Regression guard: Lavender-on-white is ~1.6:1, failing SC 1.4.11's 3:1 non-text-contrast
    // minimum — this button sits on a white card, unlike Header's navy background where Lavender
    // is correct. See the fix commit for the full explanation.
    render(<MembershipSection />)
    for (const link of screen.getAllByRole('link', { name: /continue on member jungle/i })) {
      expect(link.className).not.toContain('outline-inzbc-lavender')
    }
  })
})
