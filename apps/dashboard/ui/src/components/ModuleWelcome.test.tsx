import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ModuleWelcome } from './ModuleWelcome'

const KEY = 'inzbc.test.welcomed.v1'

beforeEach(() => window.localStorage.removeItem(KEY))
afterEach(() => vi.restoreAllMocks())

function renderWelcome() {
  return render(<ModuleWelcome storageKey={KEY} title="How this module works" steps={['First', 'Second']} />)
}

describe('ModuleWelcome', () => {
  it('shows the steps on a first visit, and folds to one link once dismissed', async () => {
    const { unmount } = renderWelcome()
    expect(screen.getByRole('heading', { name: 'How this module works' })).toBeInTheDocument()
    expect(screen.getAllByRole('listitem').map((item) => item.textContent)).toEqual(['First', 'Second'])

    await userEvent.click(screen.getByRole('button', { name: 'Got it' }))
    expect(screen.queryByRole('heading', { name: 'How this module works' })).not.toBeInTheDocument()

    unmount()
    renderWelcome()
    expect(screen.queryByRole('heading', { name: 'How this module works' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'How this works' }))
    expect(screen.getByRole('heading', { name: 'How this module works' })).toBeInTheDocument()
  })

  it('still works when storage is blocked', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    renderWelcome()
    await userEvent.click(screen.getByRole('button', { name: 'Got it' }))
    expect(screen.getByRole('button', { name: 'How this works' })).toBeInTheDocument()
  })
})
