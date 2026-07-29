import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from './App'

describe('App', () => {
  it('renders the Comms Assistant heading and the drafting form', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: /comms assistant/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/content type/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/brief/i)).toBeInTheDocument()
  })
})
