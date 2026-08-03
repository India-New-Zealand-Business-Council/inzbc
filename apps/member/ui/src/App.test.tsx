import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from './App'

describe('App', () => {
  it('renders a placeholder while the portal shell is being built', () => {
    render(<App />)
    expect(screen.getByText(/under construction/i)).toBeInTheDocument()
  })
})
