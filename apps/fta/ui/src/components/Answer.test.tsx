import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Answer } from './Answer'
import { woolAnswer } from './fixtures'

describe('Answer', () => {
  it('renders the evidence fields the Information Standard requires', () => {
    render(<Answer answer={woolAnswer} />)
    expect(screen.getByRole('heading', { name: 'Wool' })).toBeInTheDocument()
    expect(screen.getByText(/MFAT National Interest Analysis/)).toBeInTheDocument()
    expect(screen.getByText('2026-07-22')).toBeInTheDocument()
    expect(screen.getByText(/not yet in force/i)).toBeInTheDocument()
  })

  it('renders optional notes when present and omits the element when not', () => {
    const { rerender } = render(
      <Answer answer={{ ...woolAnswer, notes: 'Not a blanket dairy exclusion.' }} />,
    )
    expect(screen.getByText('Not a blanket dairy exclusion.')).toBeInTheDocument()
    rerender(<Answer answer={{ ...woolAnswer, notes: null }} />)
    expect(screen.queryByText('Not a blanket dairy exclusion.')).not.toBeInTheDocument()
  })

  it('exposes the verified date as a machine-readable time element', () => {
    render(<Answer answer={woolAnswer} />)
    expect(screen.getByText('2026-07-22').tagName).toBe('TIME')
  })
})
