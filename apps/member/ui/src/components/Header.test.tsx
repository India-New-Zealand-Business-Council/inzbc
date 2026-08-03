import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Header } from './Header'

describe('Header', () => {
  it('renders the INZBC wordmark and the Member Portal label', () => {
    render(<Header />)
    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'INZBC' })).toHaveAttribute('href', '/')
    expect(screen.getByText('Member Portal')).toBeInTheDocument()
  })

  it('provides a skip link to the main content', () => {
    render(<Header />)
    expect(screen.getByRole('link', { name: /skip to main content/i })).toHaveAttribute(
      'href',
      '#main-content',
    )
  })

  it('links to the Notifications section in primary navigation', () => {
    render(<Header />)
    expect(
      screen.getByRole('navigation', { name: 'Primary' }).querySelector('a[href="#notifications"]'),
    ).toHaveTextContent('Notifications')
  })

  it('links to the Membership section in primary navigation', () => {
    render(<Header />)
    expect(
      screen.getByRole('navigation', { name: 'Primary' }).querySelector('a[href="#membership"]'),
    ).toHaveTextContent('Membership')
  })

  it('links to the Events section in primary navigation', () => {
    render(<Header />)
    expect(
      screen.getByRole('navigation', { name: 'Primary' }).querySelector('a[href="#events"]'),
    ).toHaveTextContent('Events')
  })

  it('links to the Resources section in primary navigation', () => {
    render(<Header />)
    expect(
      screen.getByRole('navigation', { name: 'Primary' }).querySelector('a[href="#resources"]'),
    ).toHaveTextContent('Resources')
  })

  it('links Member Login out to Member Jungle rather than rendering a login form', () => {
    render(<Header />)
    const loginLink = screen.getByRole('link', { name: /member login/i })
    expect(loginLink).toHaveAttribute('href', 'https://inzbc.memberjungle.club')
    expect(loginLink).toHaveAttribute('target', '_blank')
    expect(loginLink).toHaveAttribute('rel', 'noopener noreferrer')
  })
})
