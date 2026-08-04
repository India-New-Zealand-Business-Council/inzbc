import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Dashboard } from './Dashboard'

describe('Dashboard', () => {
  it('renders the overview heading', () => {
    render(<Dashboard />)
    expect(screen.getByRole('heading', { level: 2, name: /overview/i })).toBeInTheDocument()
  })
})
