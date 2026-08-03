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
})
