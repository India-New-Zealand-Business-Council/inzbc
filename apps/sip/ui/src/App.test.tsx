import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from './App'

describe('App', () => {
  it('opens on the platform overview, not on one module', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: /inzbc platform/i })).toBeInTheDocument()
    // The overview is the landing screen because the shell now spans four modules; opening on a
    // single tool's first screen would hide the other three.
    expect(screen.getByRole('heading', { level: 2, name: /what the platform is/i })).toBeInTheDocument()
  })
})
