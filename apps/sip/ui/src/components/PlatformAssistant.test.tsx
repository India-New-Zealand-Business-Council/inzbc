import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as assistantClient from '../api/assistantClient'
import { SipApiError } from '../api/httpClient'
import { trimForServer } from '../lib/assistantHistory'
import { PlatformAssistant } from './PlatformAssistant'

afterEach(() => vi.restoreAllMocks())

describe('PlatformAssistant', () => {
  it('sends the question and shows the answer, what it looked up and the disclaimer', async () => {
    const ask = vi.spyOn(assistantClient, 'askAssistant').mockResolvedValue({
      answer: 'SIP-2026-10-24 is in QA.',
      steps: [{ tool: 'list_runs', summary: 'Listed 1 run(s)' }],
      disclaimer: 'AI-generated and advisory.',
    })
    render(<PlatformAssistant />)

    await userEvent.type(screen.getByLabelText('Your question'), 'Which run is in QA?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText('SIP-2026-10-24 is in QA.')).toBeInTheDocument()
    expect(screen.getByText('Looked up: Listed 1 run(s)')).toBeInTheDocument()
    expect(screen.getByText('AI-generated and advisory.')).toBeInTheDocument()
    expect(ask).toHaveBeenCalledWith([{ role: 'user', content: 'Which run is in QA?' }])
  })

  it('asks a suggested question in one click', async () => {
    const ask = vi
      .spyOn(assistantClient, 'askAssistant')
      .mockResolvedValue({ answer: 'Ok.', steps: [], disclaimer: 'd' })
    render(<PlatformAssistant />)

    await userEvent.click(screen.getByRole('button', { name: 'What does the FTA say about wool?' }))

    expect(await screen.findByText('Ok.')).toBeInTheDocument()
    expect(ask.mock.calls[0]?.[0]).toEqual([{ role: 'user', content: 'What does the FTA say about wool?' }])
  })

  it('says plainly when the assistant is not configured', async () => {
    vi.spyOn(assistantClient, 'askAssistant').mockRejectedValue(new SipApiError('no key', { status: 503 }))
    render(<PlatformAssistant />)

    await userEvent.type(screen.getByLabelText('Your question'), 'Hello{Enter}')

    expect(await screen.findByRole('alert')).toHaveTextContent('not configured in this environment')
  })

  // A stale disclaimer from the previous conversation must not survive into a new one -- it was
  // only "New conversation" clearing messages/error and leaving `disclaimer` state untouched.
  it('clears the disclaimer along with the conversation on New conversation', async () => {
    vi.spyOn(assistantClient, 'askAssistant').mockResolvedValue({
      answer: 'Ok.',
      steps: [],
      disclaimer: 'AI-generated and advisory.',
    })
    render(<PlatformAssistant />)

    await userEvent.type(screen.getByLabelText('Your question'), 'Hello{Enter}')
    expect(await screen.findByText('AI-generated and advisory.')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'New conversation' }))

    expect(screen.queryByText('AI-generated and advisory.')).not.toBeInTheDocument()
  })
})

describe('trimForServer', () => {
  const turn = (role: 'user' | 'assistant', length: number) => ({ role, content: 'x'.repeat(length) })

  it('keeps the newest eight turns and starts on a question', () => {
    const messages = Array.from({ length: 11 }, (_, index) => turn(index % 2 ? 'assistant' : 'user', 10))
    const kept = trimForServer(messages)
    expect(kept.length).toBeLessThanOrEqual(8)
    expect(kept[0]?.role).toBe('user')
    expect(kept.at(-1)).toBe(messages.at(-1))
  })

  it('drops older turns to stay within the character budget', () => {
    const messages = [turn('user', 1000), turn('assistant', 1000), turn('user', 1000), turn('assistant', 1000), turn('user', 1000), turn('assistant', 1000), turn('user', 1000)]
    const kept = trimForServer(messages)
    expect(kept.reduce((sum, item) => sum + item.content.length, 0)).toBeLessThanOrEqual(6000)
    expect(kept.at(-1)).toBe(messages.at(-1))
  })
})
