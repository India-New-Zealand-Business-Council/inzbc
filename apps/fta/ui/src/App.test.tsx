import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from './App'

describe('App', () => {
  it('renders the explainer heading and the query form', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: /FTA Explainer/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/ask about the nz–india fta/i)).toBeInTheDocument()
  })
})
