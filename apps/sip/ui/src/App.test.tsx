import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from './App'

describe('App', () => {
  it('renders the SIP Review heading and the default screen', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: /sip review/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: /brief builder/i })).toBeInTheDocument()
  })
})
