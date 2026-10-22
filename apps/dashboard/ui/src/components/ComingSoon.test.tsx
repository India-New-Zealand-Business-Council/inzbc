import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ComingSoon } from './ComingSoon'

describe('ComingSoon', () => {
  it('names the pending board scorecards, with no fabricated data', () => {
    render(<ComingSoon />)
    const section = screen.getByRole('heading', { name: 'Coming soon' }).closest('section')
    expect(section).toHaveTextContent('Membership')
    expect(section).toHaveTextContent('Trade / FTA')
    expect(section).toHaveTextContent('SIP scorecard')
    expect(section).toHaveTextContent('Sponsors / governance')
  })
})
