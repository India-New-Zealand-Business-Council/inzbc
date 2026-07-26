import { useId, useRef, useState } from 'react'
import { FtaQueryError, queryFta, type FtaQueryResult } from '../api/client'
import { ActionRequired } from './ActionRequired'
import { Answer } from './Answer'

type State =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'result'; result: FtaQueryResult }
  | { kind: 'error'; message: string }

export function FtaQuery({ baseUrl = '' }: { baseUrl?: string }) {
  const [query, setQuery] = useState('')
  const [state, setState] = useState<State>({ kind: 'idle' })
  const inFlight = useRef<AbortController | null>(null)
  const inputId = useId()

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = query.trim()
    if (!trimmed) return

    inFlight.current?.abort()
    const controller = new AbortController()
    inFlight.current = controller
    setState({ kind: 'loading' })

    try {
      const result = await queryFta(trimmed, { signal: controller.signal, baseUrl })
      setState({ kind: 'result', result })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      setState({
        kind: 'error',
        message:
          error instanceof FtaQueryError
            ? error.message
            : 'Something went wrong. Please try again.',
      })
    }
  }

  return (
    <section>
      <form onSubmit={onSubmit} noValidate>
        <div className="fta-field">
          <div>
            <label className="fta-label" htmlFor={inputId}>
              Ask about the NZ–India FTA
            </label>
            <input
              id={inputId}
              className="fta-input"
              name="q"
              type="search"
              maxLength={500}
              value={query}
              placeholder="e.g. dairy, wine, manuka honey"
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <button className="fta-submit" type="submit" disabled={state.kind === 'loading'}>
            {state.kind === 'loading' ? 'Searching…' : 'Search'}
          </button>
        </div>
      </form>

      {/* Results are announced rather than silently swapped in — a screen-reader user must learn
          that a no-match escalation appeared, not just that the page changed. */}
      <div aria-live="polite" aria-busy={state.kind === 'loading'}>
        {state.kind === 'error' ? (
          <p className="fta-error" role="alert">
            {state.message}
          </p>
        ) : null}

        {state.kind === 'result' && state.result.status === 'matched' ? (
          <>
            <h2>
              {state.result.answers.length} sourced{' '}
              {state.result.answers.length === 1 ? 'answer' : 'answers'}
            </h2>
            {state.result.answers.map((answer) => (
              <Answer key={answer.topic} answer={answer} />
            ))}
          </>
        ) : null}

        {/* Narrowing on `status`, never on answers.length — the generated union makes the
            compiler reject the alternative. */}
        {state.kind === 'result' && state.result.status === 'no_match' ? (
          <ActionRequired result={state.result.action_required} />
        ) : null}
      </div>
    </section>
  )
}
