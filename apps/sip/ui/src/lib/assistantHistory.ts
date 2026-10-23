import type { Turn } from '../api/assistantClient'

// The server's limits (services/api/assistant.py). The browser trims to them rather than letting
// a long conversation fail: only the newest turns are resent.
export const MAX_TURNS = 8
export const MAX_QUESTION = 1000
const BUDGET = 6000

/** The newest turns that fit the server's turn and character limits, ending with the question. */
export function trimForServer(messages: Turn[]): Turn[] {
  const kept: Turn[] = []
  let total = 0
  for (const turn of [...messages].reverse()) {
    if (kept.length >= MAX_TURNS || total + turn.content.length > BUDGET) break
    kept.unshift(turn)
    total += turn.content.length
  }
  // Dropping a leading assistant turn keeps the history reading as question-then-answer.
  while (kept.length > 1 && kept[0]?.role === 'assistant') kept.shift()
  return kept
}
