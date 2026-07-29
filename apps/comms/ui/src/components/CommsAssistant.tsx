import { useId, useRef, useState } from 'react'
import { CommsDraftError, requestCommsDraft, type ContentType } from '../api/client'

const CONTENT_TYPES: { value: ContentType; label: string }[] = [
  { value: 'newsletter', label: 'Newsletter' },
  { value: 'linkedin_post', label: 'LinkedIn Post' },
  { value: 'event_announcement', label: 'Event Announcement' },
  { value: 'member_spotlight', label: 'Member Spotlight' },
]

const BRIEF_MAX_LENGTH = 4000

type State =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'result'; draft: string }
  | { kind: 'error'; message: string }

export function CommsAssistant({ baseUrl = '' }: { baseUrl?: string }) {
  const [contentType, setContentType] = useState<ContentType>('newsletter')
  const [brief, setBrief] = useState('')
  const [state, setState] = useState<State>({ kind: 'idle' })
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'failed'>('idle')
  const inFlight = useRef<AbortController | null>(null)
  const copyResetTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const typeId = useId()
  const briefId = useId()

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = brief.trim()
    if (!trimmed) return

    inFlight.current?.abort()
    const controller = new AbortController()
    inFlight.current = controller
    setCopyStatus('idle')
    setState({ kind: 'loading' })

    try {
      const result = await requestCommsDraft(
        { contentType, brief: trimmed },
        { signal: controller.signal, baseUrl },
      )
      // Mirrors apps/fta/ui's FtaQuery: abort cannot retract an in-flight response, so only the
      // request that is still current may write state.
      if (inFlight.current !== controller) return
      setState({ kind: 'result', draft: result.draft })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      if (inFlight.current !== controller) return
      setState({
        kind: 'error',
        message:
          error instanceof CommsDraftError ? error.message : 'Something went wrong. Please try again.',
      })
    }
  }

  function onClear() {
    inFlight.current?.abort()
    inFlight.current = null
    if (copyResetTimer.current) clearTimeout(copyResetTimer.current)
    setBrief('')
    setContentType('newsletter')
    setCopyStatus('idle')
    setState({ kind: 'idle' })
  }

  async function onCopy() {
    if (state.kind !== 'result') return
    try {
      await navigator.clipboard.writeText(state.draft)
      setCopyStatus('copied')
    } catch {
      setCopyStatus('failed')
    }
    if (copyResetTimer.current) clearTimeout(copyResetTimer.current)
    copyResetTimer.current = setTimeout(() => setCopyStatus('idle'), 2000)
  }

  const isLoading = state.kind === 'loading'

  return (
    <section className="mt-6 space-y-6">
      {/* Definition of done, docs/modules/comms-assistant.md: "all outputs are drafts; external
          send/publish blocked by default". Stated on the surface so no one mistakes this for a
          send tool — there is deliberately no send/publish action anywhere in this component. */}
      <p className="rounded-md border border-inzbc-lavender bg-inzbc-lavender/10 p-3 text-sm text-inzbc-navy">
        Drafts only. Nothing here is sent or published automatically — a named human reviewer
        must approve every draft first.
      </p>

      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <div>
          <label htmlFor={typeId} className="mb-1 block font-semibold text-inzbc-navy">
            Content type
          </label>
          <select
            id={typeId}
            className="w-full rounded-md border border-slate-300 px-3 py-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
            value={contentType}
            onChange={(event) => setContentType(event.target.value as ContentType)}
          >
            {CONTENT_TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <div className="mb-1 flex items-baseline justify-between gap-3">
            <label htmlFor={briefId} className="block font-semibold text-inzbc-navy">
              Brief
            </label>
            <span
              className={`text-xs ${brief.length >= BRIEF_MAX_LENGTH ? 'font-semibold text-inzbc-crimson' : 'text-slate-500'}`}
            >
              {brief.length} / {BRIEF_MAX_LENGTH}
            </span>
          </div>
          <textarea
            id={briefId}
            className="min-h-32 w-full rounded-md border border-slate-300 px-3 py-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
            value={brief}
            maxLength={BRIEF_MAX_LENGTH}
            placeholder="Describe what you want drafted — audience, key points, tone…"
            onChange={(event) => setBrief(event.target.value)}
          />
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isLoading || brief.trim().length === 0}
            className="rounded-md bg-inzbc-tangerine px-4 py-2 font-semibold text-white disabled:cursor-progress disabled:opacity-60"
          >
            {isLoading ? 'Generating…' : 'Generate draft'}
          </button>
          <button
            type="button"
            onClick={onClear}
            className="rounded-md border border-slate-300 px-4 py-2 font-semibold text-inzbc-navy"
          >
            Clear
          </button>
        </div>
      </form>

      {/* Announced rather than silently swapped in, same reasoning as apps/fta/ui's FtaQuery. */}
      <div aria-live="polite" aria-busy={isLoading}>
        {state.kind === 'error' ? (
          <p role="alert" className="text-inzbc-crimson">
            {state.message}
          </p>
        ) : null}

        {state.kind === 'result' ? (
          <div className="space-y-2 rounded-md border border-slate-300 bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold text-inzbc-navy">Draft</h2>
              <button
                type="button"
                onClick={onCopy}
                className="rounded-md border border-slate-300 px-3 py-1 text-sm font-medium text-inzbc-navy"
              >
                {copyStatus === 'copied'
                  ? 'Copied'
                  : copyStatus === 'failed'
                    ? 'Copy failed'
                    : 'Copy to clipboard'}
              </button>
            </div>
            <pre className="whitespace-pre-wrap font-sans text-slate-800">{state.draft}</pre>
          </div>
        ) : null}
      </div>
    </section>
  )
}
