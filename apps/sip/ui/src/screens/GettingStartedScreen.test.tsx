import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as runsClient from '../api/runsClient'
import * as sessionModule from '../api/session'
import { NotSignedInError, SessionUnavailableError, seedSession } from '../api/session'
import { AppShell } from '../components/AppShell'
import { hasOnboarded, markOnboarded, resetOnboarding } from '../lib/onboarding'
import { GettingStartedScreen } from './GettingStartedScreen'

function session(roles: string[]) {
  seedSession({ userId: 'u-1', name: 'Priya Analyst', roles, csrfToken: 't' })
}

beforeEach(() => resetOnboarding())
afterEach(() => vi.restoreAllMocks())

describe('GettingStartedScreen', () => {
  it('shows the steps for each role the person holds, and only those', async () => {
    session(['Analyst', 'Reviewer'])
    render(<GettingStartedScreen onGo={vi.fn()} />)

    expect((await screen.findByText('Priya Analyst')).closest('p')).toHaveTextContent('Analyst, Reviewer')
    expect(screen.getByRole('heading', { level: 3, name: 'Analyst' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 3, name: 'Reviewer' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 3, name: 'SIP Owner' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 3, name: 'Look around' })).not.toBeInTheDocument()
    expect(screen.getByText(/rehearse it with the coordinator agent/)).toBeInTheDocument()
  })

  it('gives a read-only role the general tour', async () => {
    session(['Board Viewer'])
    render(<GettingStartedScreen onGo={vi.fn()} />)
    expect(await screen.findByRole('heading', { level: 3, name: 'Look around' })).toBeInTheDocument()
  })

  it('says when no role has been granted yet', async () => {
    session([])
    render(<GettingStartedScreen onGo={vi.fn()} />)
    expect(await screen.findByText(/no roles yet/)).toBeInTheDocument()
    expect(screen.getByText(/has to grant you a role/)).toBeInTheDocument()
  })

  it('offers sign-in when signed out', async () => {
    vi.spyOn(sessionModule, 'getSession').mockRejectedValue(new NotSignedInError('You are not signed in.'))
    render(<GettingStartedScreen onGo={vi.fn()} />)
    expect(await screen.findByRole('link', { name: 'Sign in with GitHub' })).toHaveAttribute('href', '/api/auth/github')
  })

  it('falls back to the general steps when the session cannot be checked', async () => {
    vi.spyOn(sessionModule, 'getSession').mockRejectedValue(new SessionUnavailableError('down'))
    render(<GettingStartedScreen onGo={vi.fn()} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be checked')
    expect(screen.getByRole('heading', { level: 3, name: 'Look around' })).toBeInTheDocument()
  })

  it('always says what the platform never does', async () => {
    session(['Secretariat'])
    render(<GettingStartedScreen onGo={vi.fn()} />)
    const never = (await screen.findByRole('heading', { name: 'What the platform never does' })).parentElement!
    expect(within(never).getByText(/cross a human gate/)).toBeInTheDocument()
  })

  it('sends a step to its screen', async () => {
    session(['Secretariat'])
    const onGo = vi.fn()
    render(<GettingStartedScreen onGo={onGo} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Distribution →' }))
    expect(onGo).toHaveBeenCalledWith('distribution-status')
  })
})

describe('first visit', () => {
  it('opens on Getting started once, then on the overview', async () => {
    vi.spyOn(runsClient, 'listRuns').mockResolvedValue([])
    session(['SIP Owner'])
    const first = render(<AppShell />)
    expect(screen.getByRole('heading', { level: 1, name: 'Getting started' })).toBeInTheDocument()

    await userEvent.click(await screen.findByRole('button', { name: 'CEO Decision →' }))
    expect(screen.getByRole('heading', { level: 1, name: /CEO Decision/ })).toBeInTheDocument()
    expect(hasOnboarded()).toBe(true)
    first.unmount()

    render(<AppShell />)
    expect(screen.getByRole('heading', { level: 1, name: /inzbc platform/i })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Getting started' }))
    expect(screen.getByRole('heading', { level: 1, name: 'Getting started' })).toBeInTheDocument()
  })

  it('treats blocked storage as a first visit rather than failing', () => {
    const get = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(hasOnboarded()).toBe(false)
    expect(() => markOnboarded()).not.toThrow()
    expect(() => resetOnboarding()).not.toThrow()
    expect(get).toHaveBeenCalled()
  })
})
