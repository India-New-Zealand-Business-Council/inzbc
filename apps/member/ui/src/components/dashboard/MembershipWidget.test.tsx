import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MembershipWidget } from './MembershipWidget'

describe('MembershipWidget', () => {
  it('lists the Join/Renew, Directory and Billing actions, linking each to Member Jungle', () => {
    render(<MembershipWidget />)

    for (const name of ['Join / Renew', 'Member Directory', 'Billing & Invoices']) {
      const link = screen.getByRole('link', { name })
      expect(link).toHaveAttribute('href', 'https://inzbc.memberjungle.club')
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    }
  })

  it('links to the full Membership section', () => {
    render(<MembershipWidget />)
    expect(screen.getByRole('link', { name: /view membership details/i })).toHaveAttribute(
      'href',
      '#membership',
    )
  })
})
