import type { components } from './schema'
import { apiRequest, type RequestOptions } from './httpClient'

export type ChatIn = components['schemas']['ChatIn']
export type ChatOut = components['schemas']['ChatOut']
export type Turn = components['schemas']['Turn']

const JSON_HEADERS = { 'Content-Type': 'application/json', Accept: 'application/json' } as const

/**
 * One turn with the platform assistant (`services/api/assistant.py`). The browser holds the
 * conversation and resends it; the server stores none of it.
 */
export async function askAssistant(messages: Turn[], options: RequestOptions = {}): Promise<ChatOut> {
  const { signal, baseUrl = '' } = options
  const body: ChatIn = { messages }
  return apiRequest<ChatOut>(`${baseUrl}/api/assistant/chat`, {
    method: 'POST',
    signal,
    credentials: 'same-origin',
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  })
}
