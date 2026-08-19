import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Header } from './Header'

describe('Header', () => {
  it('renders the INZBC wordmark and the current page in primary navigation', () => {
    render(<Header />)
    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'INZBC' })).toHaveAttribute('href', '/')
    expect(
      screen.getByRole('navigation', { name: 'Primary' }).querySelector('[aria-current="page"]'),
    ).toHaveTextContent('FTA Explainer')
  })

  it('provides a skip link to the main content', () => {
    render(<Header />)
    expect(screen.getByRole('link', { name: /skip to main content/i })).toHaveAttribute(
      'href',
      '#main-content',
    )
  })
})
