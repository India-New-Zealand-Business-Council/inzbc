import { useEffect, useId, useRef, useState } from 'react'
import {
  CommsDraftError,
  KEY_POINT_MAX_LENGTH,
  MAX_KEY_POINTS,
  MAX_LINKS,
  TOPIC_MAX_LENGTH,
  TOTAL_BRIEF_BUDGET,
  requestCommsDraft,
  type ContentType,
  type Tone,
} from '../api/client'

/** Splits a textarea into trimmed, non-empty lines. */
function lines(value: string): string[] {
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}
import { downloadAsWord, exportAsPdf } from '../lib/exportDraft'

const CONTENT_TYPES: { value: ContentType; label: string }[] = [
  { value: 'newsletter', label: 'Newsletter' },
  { value: 'linkedin_post', label: 'LinkedIn Post' },
  { value: 'event_announcement', label: 'Event Announcement' },
  { value: 'member_spotlight', label: 'Member Spotlight' },
]

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
  // #303: the single 4,000-character brief became named fields. Key points and links are held as
  // one textarea each, split on newlines, rather than eight and five separate inputs - same data,
  // far less markup, and it keeps the paste-a-list habit people already have.
  const [topic, setTopic] = useState('')
  const [keyPointsText, setKeyPointsText] = useState('')
  const [linksText, setLinksText] = useState('')
  const [tone, setTone] = useState<Tone>('formal')
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
  const topicId = useId()
  const keyPointsId = useId()
  const linksId = useId()
  const toneId = useId()
  const warningId = useId()

  const keyPoints = lines(keyPointsText)
  const links = lines(linksText)

  // Every rule below mirrors one the server enforces. Adversarial review found the previous
  // version let the user submit states the server rejects, so the red counters were decorative
  // and the only feedback was a bare "returned 422".
  //
  // Topic is required, not optional: `DraftIn.topic` has min_length=1. The earlier rule here
  // allowed a key-points-only brief, which the server refuses every time.
  const overLongKeyPoints = keyPoints.filter((point) => point.length > KEY_POINT_MAX_LENGTH)
  const totalChars =
    topic.trim().length +
    keyPoints.reduce((sum, point) => sum + point.length, 0) +
    links.reduce((sum, link) => sum + link.length, 0)
  const problems: string[] = []
  if (keyPoints.length > MAX_KEY_POINTS) problems.push(`No more than ${MAX_KEY_POINTS} key points.`)
  if (links.length > MAX_LINKS) problems.push(`No more than ${MAX_LINKS} links.`)
  if (overLongKeyPoints.length > 0)
    problems.push(`Each key point must be ${KEY_POINT_MAX_LENGTH} characters or fewer.`)
  if (totalChars > TOTAL_BRIEF_BUDGET)
    problems.push(`The brief is ${totalChars} characters; the limit is ${TOTAL_BRIEF_BUDGET}.`)

  const canSubmit = topic.trim().length > 0 && problems.length === 0

  async function generateDraft() {
    if (!canSubmit) return

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
        { contentType, topic: topic.trim(), keyPoints },
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

  function onBriefKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement | HTMLInputElement>) {
    // Ctrl+Enter (Cmd+Enter on macOS) submits without leaving the keyboard — plain Enter stays a
    // newline, since key points and links are one per line.
    //
    // Attached to every brief field including the topic input, not only the textareas. #303 split
    // one textarea into four controls; leaving the shortcut on the textareas alone would mean it
    // worked or not depending on which field happened to have focus.
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault()
      void generateDraft()
      return
    }
    // Plain Enter in the topic field must not submit. A lone <input> inside a <form> submits on
    // Enter natively, so splitting the old textarea into named fields (#303) would otherwise have
    // quietly turned a deliberate Ctrl+Enter-only design into accidental-submit-while-typing.
    // The textareas need no such guard: Enter is a newline there, which is what they are for.
    if (event.key === 'Enter' && event.currentTarget instanceof HTMLInputElement) {
      event.preventDefault()
    }
  }

  function onClear() {
    inFlight.current?.abort()
    inFlight.current = null
    if (copyResetTimer.current) clearTimeout(copyResetTimer.current)
    // Aborting the request does not run the catch block that would normally clear this, so
    // clearing mid-generation used to leave the form stuck in its generating state until reload.
    setIsGenerating(false)
    setTopic('')
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
            <label htmlFor={topicId} className="block font-semibold text-inzbc-navy">
              Topic
            </label>
            <span
              id={`${topicId}-count`}
              className={`text-xs ${topic.length >= TOPIC_MAX_LENGTH ? 'font-semibold text-inzbc-crimson' : 'text-slate-500'}`}
            >
              {topic.length} / {TOPIC_MAX_LENGTH}
            </span>
          </div>
          <input
            id={topicId}
            type="text"
            // The counter and the prohibited-data warning are announced with the field rather than
            // being visual-only. Without this a screen reader user reaches the input with no idea
            // there is a limit or that the text goes to an external model (WCAG 3.3.2).
            aria-describedby={`${topicId}-count ${warningId}`}
            className="w-full rounded-md border border-inzbc-navy/20 px-3 py-2 transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
            value={topic}
            maxLength={TOPIC_MAX_LENGTH}
            placeholder="What is this piece about?"
            onChange={(event) => setTopic(event.target.value)}
            onKeyDown={onBriefKeyDown}
          />
        </div>

        <div>
          <div className="mb-1 flex items-baseline justify-between gap-3">
            <label htmlFor={keyPointsId} className="block font-semibold text-inzbc-navy">
              Key points
            </label>
            <span
              id={`${keyPointsId}-count`}
              className={`text-xs ${keyPoints.length > MAX_KEY_POINTS ? 'font-semibold text-inzbc-crimson' : 'text-slate-500'}`}
            >
              {keyPoints.length} / {MAX_KEY_POINTS}
            </span>
          </div>
          <textarea
            id={keyPointsId}
            aria-describedby={`${keyPointsId}-count ${keyPointsId}-help ${warningId}`}
            className="min-h-24 w-full rounded-md border border-inzbc-navy/20 px-3 py-2 transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
            value={keyPointsText}
            placeholder={`One per line, up to ${MAX_KEY_POINTS}.`}
            onChange={(event) => setKeyPointsText(event.target.value)}
            onKeyDown={onBriefKeyDown}
          />
          <p id={`${keyPointsId}-help`} className="mt-1 text-xs text-slate-500">
            One per line, {KEY_POINT_MAX_LENGTH} characters each.
          </p>
        </div>

        {/* The prohibited-data warning applies to every field, not just key points. It sat under
            key points alone, which left it absent from Topic and Links — the two fields the code
            itself names as carrying the residual #303 risk. Referenced by all four via
            aria-describedby so it is announced wherever the user is typing. */}
        <p id={warningId} className="text-xs text-slate-600">
          <strong className="font-semibold text-inzbc-navy">This text is sent to an external
          model.</strong>{' '}
          Do not enter member names, job titles, employers or Board material in any field. Redaction
          removes formatted identifiers such as emails and phone numbers; it cannot remove a name.
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <div className="mb-1 flex items-baseline justify-between gap-3">
              <label htmlFor={linksId} className="block font-semibold text-inzbc-navy">
                Links
              </label>
              <span
                id={`${linksId}-count`}
                className={`text-xs ${links.length > MAX_LINKS ? 'font-semibold text-inzbc-crimson' : 'text-slate-500'}`}
              >
                {links.length} / {MAX_LINKS}
              </span>
            </div>
            <textarea
              id={linksId}
              aria-describedby={`${linksId}-count ${warningId}`}
              className="min-h-20 w-full rounded-md border border-inzbc-navy/20 px-3 py-2 transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
              value={linksText}
              placeholder="One URL per line."
              onChange={(event) => setLinksText(event.target.value)}
              onKeyDown={onBriefKeyDown}
            />
          </div>

          <div>
            <label htmlFor={toneId} className="mb-1 block font-semibold text-inzbc-navy">
              Tone
            </label>
            <select
              id={toneId}
              className="w-full rounded-md border border-inzbc-navy/20 px-3 py-2 transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
              value={tone}
              onChange={(event) => setTone(event.target.value as Tone)}
            >
              <option value="formal">Formal</option>
              <option value="warm">Warm</option>
              <option value="concise">Concise</option>
            </select>
            <p className="mt-1 text-xs text-slate-500">Ctrl+Enter (⌘+Enter on Mac) to generate.</p>
          </div>
        </div>

        {problems.length > 0 && (
          // A disabled button with no stated reason is the failure this replaces: the counters
          // turned red and nothing said why submit stopped working. Colour was also the only
          // signal, which fails WCAG 1.4.1 — this gives the same information as text.
          <ul role="alert" className="list-disc space-y-1 pl-5 text-sm text-inzbc-crimson">
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isLoading || !canSubmit}
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
