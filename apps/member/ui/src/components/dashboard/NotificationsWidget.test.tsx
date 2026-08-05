import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PLACEHOLDER_NOTIFICATIONS } from '../../lib/notificationsData'
import { NotificationsWidget } from './NotificationsWidget'

describe('NotificationsWidget', () => {
  it('shows the first two placeholder-labelled notifications reused from the full section', () => {
    render(<NotificationsWidget />)
    expect(screen.getAllByText('Placeholder')).toHaveLength(2)
    expect(screen.getAllByText(PLACEHOLDER_NOTIFICATIONS[0]!.text)).toHaveLength(2)
  })

  it('links to the full Notifications section', () => {
    render(<NotificationsWidget />)
    expect(screen.getByRole('link', { name: /view all notifications/i })).toHaveAttribute(
      'href',
      '#notifications',
    )
  })
})
