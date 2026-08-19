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
      // Abort alone is not enough: if a response has already arrived when the next search
      // starts, aborting cannot retract it, and this continuation would overwrite the newer
      // result. Only the request that is still current may set state.
      if (inFlight.current !== controller) return
      setState({ kind: 'result', result })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      if (inFlight.current !== controller) return
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
    <section className="mt-6">
      <form onSubmit={onSubmit} noValidate className="flex flex-wrap items-end gap-2">
        <div className="min-w-72 flex-1">
          <label htmlFor={inputId} className="mb-1 block text-sm font-semibold text-inzbc-navy">
            Ask about the NZ–India FTA
          </label>
          <input
            id={inputId}
            name="q"
            type="search"
            maxLength={500}
            value={query}
            placeholder="e.g. dairy, wine, manuka honey"
            onChange={(event) => setQuery(event.target.value)}
            className="w-full rounded-md border border-inzbc-navy/20 px-3 py-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
          />
        </div>
        <button
          type="submit"
          disabled={state.kind === 'loading'}
          // min-h-11: 44px minimum touch target (WCAG 2.5.8), same as apps/comms/ui's icon
          // buttons. Navy text on tangerine, not white: white-on-tangerine is 3.37:1 against the
          // 4.5:1 AA minimum, navy-on-tangerine is 5.56:1 — same fix applied to every primary
          // button in apps/comms/ui and apps/sip/ui.
          className="min-h-11 rounded-md bg-inzbc-tangerine px-4 py-2 text-sm font-semibold text-inzbc-navy transition-colors hover:enabled:bg-inzbc-tangerine/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue disabled:cursor-progress disabled:opacity-60"
        >
          {state.kind === 'loading' ? 'Searching…' : 'Search'}
        </button>
      </form>

      {/* Results are announced rather than silently swapped in — a screen-reader user must learn
          that a no-match escalation appeared, not just that the page changed. */}
      <div aria-live="polite" aria-busy={state.kind === 'loading'}>
        {state.kind === 'error' ? (
          <p role="alert" className="mt-4 text-sm font-medium text-inzbc-crimson">
            {state.message}
          </p>
        ) : null}

        {state.kind === 'result' && state.result.status === 'matched' ? (
          <>
            <h2 className="mt-6 text-lg font-bold text-inzbc-navy sm:text-xl">
              {state.result.answers.length} sourced{' '}
              {state.result.answers.length === 1 ? 'answer' : 'answers'}
            </h2>
            {state.result.answers.map((answer) => (
              <Answer key={answer.id} answer={answer} />
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
