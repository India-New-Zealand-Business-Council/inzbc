import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from './App'

describe('App', () => {
  it('renders the Member Portal heading and explains the link-out model', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: /member portal/i })).toBeInTheDocument()
    expect(screen.getByText(/managed on member jungle/i)).toBeInTheDocument()
  })

  it('renders the header and footer', () => {
    render(<App />)
    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('contentinfo')).toBeInTheDocument()
  })

  it("makes the skip link's target focusable, so activating it actually moves focus", () => {
    render(<App />)
    // A plain <main> isn't in the browser's focusable-elements set — without tabIndex=-1,
    // Header's "Skip to main content" link would scroll here without moving keyboard/AT focus
    // (WCAG technique G1/H69). document.getElementById, not getByRole, because <main> has no
    // accessible name and getByRole('main') would still pass even without the fix.
    expect(document.getElementById('main-content')).toHaveAttribute('tabindex', '-1')
  })

  it('renders the Notifications section', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 2, name: /^notifications$/i })).toBeInTheDocument()
  })

  it('renders the Membership section', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 2, name: /^membership$/i })).toBeInTheDocument()
  })

  it('renders the Events section', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 2, name: /upcoming events/i })).toBeInTheDocument()
  })

  it('renders the Resources section', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 2, name: /^resources$/i })).toBeInTheDocument()
  })
})
