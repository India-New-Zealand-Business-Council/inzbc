import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Container } from './Container'

describe('Container', () => {
  it('renders its children within the shared max-width', () => {
    render(
      <Container>
        <p>content</p>
      </Container>,
    )
    const content = screen.getByText('content')
    expect(content.parentElement).toHaveClass('max-w-7xl')
  })

  it('merges an additional className with its own', () => {
    render(
      <Container className="py-4">
        <p>content</p>
      </Container>,
    )
    const content = screen.getByText('content')
    expect(content.parentElement).toHaveClass('max-w-7xl', 'py-4')
  })
})
