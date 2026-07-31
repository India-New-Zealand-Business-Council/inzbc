import { useEffect, useId, useRef, useState } from 'react'
import { CommsDraftError, requestCommsDraft, type ContentType } from '../api/client'
import { downloadAsWord, exportAsPdf } from '../lib/exportDraft'

const CONTENT_TYPES: { value: ContentType; label: string }[] = [
  { value: 'newsletter', label: 'Newsletter' },
  { value: 'linkedin_post', label: 'LinkedIn Post' },
  { value: 'event_announcement', label: 'Event Announcement' },
  { value: 'member_spotlight', label: 'Member Spotlight' },
]

const BRIEF_MAX_LENGTH = 4000
const HISTORY_LIMIT = 3

const CONTENT_TYPE_LABELS = Object.fromEntries(
  CONTENT_TYPES.map((option) => [option.value, option.label]),
) as Record<ContentType, string>

function countWords(text: string): number {
  const trimmed = text.trim()
  return trimmed === '' ? 0 : trimmed.split(/\s+/).length
}

// Displayed draft and in-flight/error status are deliberately separate pieces of state (they used
// to be one tagged union collapsed onto 'loading' the instant a regenerate started). Generate A,
// ask for a revision, hit a 503: with one combined state, the loading transition had already
// overwritten A before the request failed, so the error replaced a draft that still existed
// server-side — there was no way back to it. Keeping `draftState` untouched by a failed
// `generateDraft` call means the previous draft simply stays on screen while `submitError` reports
// what went wrong alongside it.
type DraftState = { kind: 'idle' } | { kind: 'result'; draft: string; contentType: ContentType }

interface HistoryEntry {
  id: string
  contentType: ContentType
  draft: string
}

export function CommsAssistant({ baseUrl = '' }: { baseUrl?: string }) {
  const [contentType, setContentType] = useState<ContentType>('newsletter')
  const [brief, setBrief] = useState('')
  const [draftState, setDraftState] = useState<DraftState>({ kind: 'idle' })
  const [isGenerating, setIsGenerating] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'failed'>('idle')
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null)
  const inFlight = useRef<AbortController | null>(null)
  const copyResetTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Unmounting mid-request otherwise leaves the fetch running and the copy-status timer armed,
  // both of which would call setState on a component that no longer exists.
  useEffect(
    () => () => {
      inFlight.current?.abort()
      if (copyResetTimer.current) clearTimeout(copyResetTimer.current)
    },
    [],
  )
  const typeId = useId()
  const briefId = useId()

  async function generateDraft() {
    const trimmed = brief.trim()
    if (!trimmed) return

    // Captured before the request starts, so history keeps the content type that was actually
    // selected when this draft was generated — not whatever the dropdown reads later.
    const outgoing = draftState.kind === 'result' ? draftState : null

    inFlight.current?.abort()
    const controller = new AbortController()
    inFlight.current = controller
    setCopyStatus('idle')
    setSubmitError(null)
    setIsGenerating(true)

    try {
      const result = await requestCommsDraft(
        { contentType, brief: trimmed },
        { signal: controller.signal, baseUrl },
      )
      // Mirrors apps/fta/ui's FtaQuery: abort cannot retract an in-flight response, so only the
      // request that is still current may write state.
      if (inFlight.current !== controller) return
      if (outgoing) {
        setHistory((prev) =>
          [{ id: crypto.randomUUID(), contentType: outgoing.contentType, draft: outgoing.draft }, ...prev].slice(
            0,
            HISTORY_LIMIT,
          ),
        )
      }
      setFeedback(null)
      setDraftState({ kind: 'result', draft: result.draft, contentType })
      setIsGenerating(false)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      if (inFlight.current !== controller) return
      setIsGenerating(false)
      // draftState is deliberately untouched here — see the type's comment above.
      setSubmitError(
        error instanceof CommsDraftError ? error.message : 'Something went wrong. Please try again.',
      )
    }
  }

  function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    void generateDraft()
  }

  function onBriefKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Ctrl+Enter (Cmd+Enter on macOS) submits without leaving the keyboard — plain Enter stays a
    // newline, since a brief is often more than one line.
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault()
      void generateDraft()
    }
  }

  function onClear() {
    inFlight.current?.abort()
    inFlight.current = null
    if (copyResetTimer.current) clearTimeout(copyResetTimer.current)
    setBrief('')
    setContentType('newsletter')
    setCopyStatus('idle')
    setFeedback(null)
    setSubmitError(null)
    // History goes too. Leaving prior drafts on screen after Clear is the wrong default for a
    // surface that will carry member and commercial material once /api/comms/draft exists, and
    // it is not what the control appears to promise.
    setHistory([])
    setDraftState({ kind: 'idle' })
  }

  function onFeedback(value: 'up' | 'down') {
    setFeedback((previous) => (previous === value ? null : value))
  }

  async function onCopy() {
    if (draftState.kind !== 'result') return
    try {
      await navigator.clipboard.writeText(draftState.draft)
      setCopyStatus('copied')
    } catch {
      setCopyStatus('failed')
    }
    if (copyResetTimer.current) clearTimeout(copyResetTimer.current)
    copyResetTimer.current = setTimeout(() => setCopyStatus('idle'), 2000)
  }

  const isLoading = isGenerating

  return (
    <section className="mt-6 space-y-6">
      {/* Definition of done, docs/modules/comms-assistant.md: "all outputs are drafts; external
          send/publish blocked by default". Stated on the surface so no one mistakes this for a
          send tool — there is deliberately no send/publish action anywhere in this component. */}
      <p className="rounded-md border border-inzbc-lavender bg-inzbc-lavender/10 p-3 text-sm text-inzbc-navy">
        <strong className="font-semibold">AI drafts require human review before publishing.</strong>{' '}
        Drafts only — nothing here is sent or published automatically; a named human reviewer
        must approve every draft first.
      </p>

      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <div>
          <label htmlFor={typeId} className="mb-1 block font-semibold text-inzbc-navy">
            Content type
          </label>
          <select
            id={typeId}
            className="w-full rounded-md border border-inzbc-navy/20 px-3 py-2 transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
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
            className="min-h-32 w-full rounded-md border border-inzbc-navy/20 px-3 py-2 transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
            value={brief}
            maxLength={BRIEF_MAX_LENGTH}
            placeholder="Describe what you want drafted — audience, key points, tone…"
            onChange={(event) => setBrief(event.target.value)}
            onKeyDown={onBriefKeyDown}
          />
          <p className="mt-1 text-xs text-slate-500">Ctrl+Enter (⌘+Enter on Mac) to generate.</p>
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isLoading || brief.trim().length === 0}
            className="rounded-md bg-inzbc-tangerine px-4 py-2 font-semibold text-inzbc-navy transition-colors hover:enabled:bg-inzbc-tangerine/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue disabled:cursor-progress disabled:opacity-60"
          >
            {isLoading ? 'Generating…' : 'Generate draft'}
          </button>
          <button
            type="button"
            onClick={onClear}
            className="rounded-md border border-slate-300 px-4 py-2 font-semibold text-inzbc-navy transition-colors hover:border-inzbc-navy hover:bg-inzbc-navy/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
          >
            Clear
          </button>
        </div>
      </form>

      {/* Announced rather than silently swapped in, same reasoning as apps/fta/ui's FtaQuery. */}
      <div aria-live="polite" aria-busy={isLoading}>
        {submitError ? (
          <p role="alert" className="text-inzbc-crimson">
            {submitError}
          </p>
        ) : null}

        {/* Purely visual — aria-busy above already tells assistive tech generation is under way,
            so this skeleton is hidden from the accessibility tree rather than announced twice.
            Only shown for a first-ever draft: a regeneration (draftState already holds a result)
            keeps that result on screen instead — see the inline "Generating…" note below rather
            than replacing it with a skeleton, which is what used to make a failed regeneration
            look like the previous draft had been destroyed. */}
        {isLoading && draftState.kind === 'idle' ? (
          <div aria-hidden="true" className="space-y-3 rounded-md border border-slate-300 bg-white p-5 shadow-sm">
            <div className="h-4 w-1/3 animate-pulse rounded bg-slate-200" />
            <div className="space-y-2">
              <div className="h-3 w-full animate-pulse rounded bg-slate-200" />
              <div className="h-3 w-full animate-pulse rounded bg-slate-200" />
              <div className="h-3 w-5/6 animate-pulse rounded bg-slate-200" />
              <div className="h-3 w-2/3 animate-pulse rounded bg-slate-200" />
            </div>
          </div>
        ) : null}

        {draftState.kind === 'result' ? (
          <div className="space-y-2 rounded-md border border-slate-300 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              {/* family/weight/uppercase from index.css's @layer base h2 rule; the word count is
                  reset back to normal-case body copy since it's fine print, not a heading. */}
              <h2 className="text-base text-inzbc-navy sm:text-lg">
                Draft{' '}
                <span className="font-[family-name:var(--font-body)] text-sm font-normal normal-case text-slate-500">
                  · {countWords(draftState.draft)} words
                  {isLoading ? ' · Generating a new draft…' : ''}
                </span>
              </h2>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={onCopy}
                  className="rounded-md border border-slate-300 px-3 py-1 text-sm font-medium text-inzbc-navy transition-colors hover:border-inzbc-navy hover:bg-inzbc-navy/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
                >
                  {copyStatus === 'copied'
                    ? 'Copied'
                    : copyStatus === 'failed'
                      ? 'Copy failed'
                      : 'Copy to clipboard'}
                </button>
                <button
                  type="button"
                  onClick={() => downloadAsWord(draftState.draft, `${draftState.contentType}-draft`)}
                  className="rounded-md border border-slate-300 px-3 py-1 text-sm font-medium text-inzbc-navy transition-colors hover:border-inzbc-navy hover:bg-inzbc-navy/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
                >
                  Export as Word
                </button>
                <button
                  type="button"
                  onClick={exportAsPdf}
                  className="rounded-md border border-slate-300 px-3 py-1 text-sm font-medium text-inzbc-navy transition-colors hover:border-inzbc-navy hover:bg-inzbc-navy/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
                >
                  Export as PDF
                </button>
              </div>
            </div>
            <pre className="print-draft whitespace-pre-wrap font-sans text-slate-800">{draftState.draft}</pre>

            {/* Local UI state only — no feedback endpoint exists or is specified anywhere
                (docs/api-integration-spec.md documents no such contract), so this isn't wired to
                a network call. Wiring it up is future work once a feedback mechanism is decided,
                not something to invent a proposed contract for here. */}
            <div className="flex flex-wrap items-center gap-2 border-t border-slate-200 pt-2 text-sm text-slate-600">
              <span>Was this draft helpful?</span>
              {/* min-h/min-w-11 (44px) rather than the compact px-2 py-1 used elsewhere in this
                  component: these are icon-only with no text to pad the hit area out, so they
                  need an explicit floor to clear a comfortable mobile touch target. */}
              <button
                type="button"
                aria-pressed={feedback === 'up'}
                aria-label="Helpful"
                onClick={() => onFeedback('up')}
                className={`flex min-h-11 min-w-11 items-center justify-center rounded-md border text-lg transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue ${
                  feedback === 'up'
                    ? 'border-inzbc-forest bg-inzbc-forest/10 text-inzbc-forest'
                    : 'border-slate-300 text-inzbc-navy hover:border-inzbc-forest hover:bg-inzbc-forest/5'
                }`}
              >
                <span aria-hidden="true">👍</span>
              </button>
              <button
                type="button"
                aria-pressed={feedback === 'down'}
                aria-label="Not helpful"
                onClick={() => onFeedback('down')}
                className={`flex min-h-11 min-w-11 items-center justify-center rounded-md border text-lg transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue ${
                  feedback === 'down'
                    ? 'border-inzbc-crimson bg-inzbc-crimson/10 text-inzbc-crimson'
                    : 'border-slate-300 text-inzbc-navy hover:border-inzbc-crimson hover:bg-inzbc-crimson/5'
                }`}
              >
                <span aria-hidden="true">👎</span>
              </button>
              {feedback ? <span className="text-xs text-slate-500">Thanks — noted for this session only.</span> : null}
            </div>
          </div>
        ) : null}
      </div>

      {history.length > 0 ? (
        <div className="space-y-2">
          <h2 className="text-base text-inzbc-navy sm:text-lg">Recent drafts</h2>
          <ul className="space-y-2">
            {history.map((entry) => (
              <li key={entry.id} className="rounded-md border border-slate-200 bg-slate-50 p-4 shadow-sm">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {CONTENT_TYPE_LABELS[entry.contentType]}
                </p>
                <p className="max-h-24 overflow-y-auto whitespace-pre-wrap text-sm text-slate-700">
                  {entry.draft}
                </p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {copyStatus !== 'idle' ? (
        // inset-x-4 on narrow viewports so the toast can never overflow a 320px-wide screen
        // (WCAG 2.2 §1.4.10 reflow); from sm: up there's room to right-anchor it as a compact
        // pill instead of spanning full width.
        <div
          role="status"
          className={`fixed inset-x-4 bottom-4 z-50 rounded-md px-4 py-2 text-center text-sm font-medium text-white shadow-lg sm:inset-x-auto sm:right-4 sm:text-left ${
            copyStatus === 'copied' ? 'bg-inzbc-forest' : 'bg-inzbc-crimson'
          }`}
        >
          {copyStatus === 'copied' ? 'Copied to clipboard' : "Couldn't copy to clipboard"}
        </div>
      ) : null}
    </section>
  )
}
