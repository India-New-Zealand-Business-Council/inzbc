import { useRef, useState, type FormEvent } from 'react'
import { askAssistant, type ChatOut, type Turn } from '../api/assistantClient'
import { SipApiError } from '../api/httpClient'
import { MAX_QUESTION, trimForServer } from '../lib/assistantHistory'

const SUGGESTIONS = [
  'Which runs are waiting on QA?',
  'What does the FTA say about wool?',
  'Who can approve a Comms draft?',
]

interface Message extends Turn {
  steps?: ChatOut['steps']
}

function errorText(error: unknown): string {
  if (error instanceof SipApiError) {
    if (error.status === 401) return 'Sign in to use the assistant.'
    if (error.status === 503) return 'The assistant is not configured in this environment yet.'
    if (error.status === 422) return error.message
  }
  return 'The assistant could not answer just now. Try again in a moment.'
}

/**
 * The platform assistant: a chat agent that can only read. It looks things up with three tools
 * (FTA corpus, recent runs, the platform guide) and answers; it cannot change anything.
 */
export function PlatformAssistant() {
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [disclaimer, setDisclaimer] = useState<string | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const send = async (question: string) => {
    const text = question.trim()
    if (!text || busy) return
    const next: Message[] = [...messages, { role: 'user', content: text }]
    setMessages(next)
    setDraft('')
    setError(null)
    setBusy(true)
    try {
      const reply = await askAssistant(
        trimForServer(next.map(({ role, content }) => ({ role, content }))),
      )
      setMessages([...next, { role: 'assistant', content: reply.answer, steps: reply.steps }])
      setDisclaimer(reply.disclaimer)
    } catch (cause) {
      setError(errorText(cause))
    } finally {
      setBusy(false)
      inputRef.current?.focus()
    }
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    void send(draft)
  }

  return (
    <section
      aria-labelledby="assistant-heading"
      className="rounded-2xl border border-inzbc-ink/10 bg-white p-6 shadow-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 id="assistant-heading" className="text-lg font-bold text-inzbc-navy">
            Ask the platform assistant
          </h2>
          <p className="mt-1 max-w-3xl text-sm text-slate-700">
            An AI agent that can look up FTA guidance, the state of recent runs and how each
            module works. It can only read: it cannot change a run, record a decision or send
            anything. Do not type member personal data here.
          </p>
        </div>
        {messages.length ? (
          <button
            type="button"
            onClick={() => {
              setMessages([])
              setError(null)
            }}
            className="min-h-11 px-2 text-sm font-medium text-inzbc-blue underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
          >
            New conversation
          </button>
        ) : null}
      </div>

      <ol aria-live="polite" aria-label="Conversation" className="mt-4 space-y-3">
        {messages.map((message, index) => (
          <li
            key={index}
            className={`rounded-xl p-3 text-sm ${
              message.role === 'user' ? 'ml-auto max-w-[85%] bg-inzbc-mist/70 text-inzbc-ink' : 'max-w-[85%] border border-inzbc-ink/10 bg-white text-slate-800'
            }`}
          >
            <span className="sr-only">{message.role === 'user' ? 'You' : 'Assistant'}: </span>
            <p className="whitespace-pre-wrap">{message.content}</p>
            {message.steps?.length ? (
              <p className="mt-2 text-xs text-slate-500">Looked up: {message.steps.map((step) => step.summary).join('; ')}</p>
            ) : null}
          </li>
        ))}
        {busy ? (
          <li role="status" className="text-sm text-slate-600">
            Looking that up…
          </li>
        ) : null}
      </ol>

      {messages.length === 0 ? (
        <ul aria-label="Suggested questions" className="mt-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <li key={suggestion}>
              <button
                type="button"
                onClick={() => void send(suggestion)}
                className="min-h-11 rounded-full border border-inzbc-ink/15 px-3 py-1.5 text-sm text-inzbc-ink hover:bg-inzbc-mist/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
              >
                {suggestion}
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {error ? (
        <p role="alert" className="mt-3 text-sm text-inzbc-crimson">
          {error}
        </p>
      ) : null}

      <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-end">
        <label htmlFor="assistant-question" className="sr-only">
          Your question
        </label>
        <textarea
          id="assistant-question"
          ref={inputRef}
          value={draft}
          maxLength={MAX_QUESTION}
          rows={2}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              void send(draft)
            }
          }}
          placeholder="Ask about runs, the FTA or how the platform works"
          className="min-h-11 w-full flex-1 resize-y rounded-md border border-inzbc-ink/20 p-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
        />
        <button
          type="submit"
          disabled={busy || !draft.trim()}
          className="min-h-11 rounded-md bg-inzbc-tangerine px-4 py-2 text-sm font-semibold text-inzbc-navy transition-colors hover:bg-inzbc-tangerine/90 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
        >
          Ask
        </button>
      </form>
      {disclaimer ? <p className="mt-2 text-xs text-slate-500">{disclaimer}</p> : null}
    </section>
  )
}
