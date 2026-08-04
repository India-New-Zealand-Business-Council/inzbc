import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DashboardCard } from './DashboardCard'

describe('DashboardCard', () => {
  it('exposes itself as a labelled group, named by its own title', () => {
    render(
      <DashboardCard title="Widget Title" linkHref="#section" linkLabel="View all">
        <p>content</p>
      </DashboardCard>,
    )
    expect(screen.getByRole('group', { name: 'Widget Title' })).toBeInTheDocument()
  })

  it('renders the view-all link with the given href and label', () => {
    render(
      <DashboardCard title="Widget Title" linkHref="#section" linkLabel="View all">
        <p>content</p>
      </DashboardCard>,
    )
    expect(screen.getByRole('link', { name: 'View all' })).toHaveAttribute('href', '#section')
  })
})
