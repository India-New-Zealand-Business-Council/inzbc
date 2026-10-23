import { useState } from 'react'

// Copied into each app's components/ (fta, comms, dashboard, member, sip), the same way each
// app carries its own Header and Footer: the apps build separately and share no package. Keep the
// copies identical; only each app's Welcome.tsx content differs.

interface Props {
  /** One key per module, so dismissing one module's introduction leaves the others. */
  storageKey: string
  title: string
  steps: string[]
}

function seen(key: string): boolean {
  try {
    return window.localStorage.getItem(key) === 'yes'
  } catch {
    return false
  }
}

function remember(key: string, value: boolean): void {
  try {
    if (value) window.localStorage.setItem(key, 'yes')
    else window.localStorage.removeItem(key)
  } catch {
    // Storage blocked: the introduction shows again next visit, which costs one click.
  }
}

/**
 * A module's first-visit introduction: what it is for and how to use it, in a few steps. Shown
 * until dismissed, then folded to one link so it is never more than a click away.
 */
export function ModuleWelcome({ storageKey, title, steps }: Props) {
  const [open, setOpen] = useState(() => !seen(storageKey))

  if (!open) {
    return (
      <p className="mb-4 text-sm">
        <button
          type="button"
          onClick={() => {
            remember(storageKey, false)
            setOpen(true)
          }}
          className="min-h-11 font-medium text-inzbc-blue underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
        >
          How this works
        </button>
      </p>
    )
  }

  return (
    <section
      aria-label={title}
      className="mb-6 rounded-xl border border-inzbc-navy/10 bg-white p-4 shadow-sm"
    >
      <h2 className="text-base font-semibold text-inzbc-navy">{title}</h2>
      <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-700">
        {steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <button
        type="button"
        onClick={() => {
          remember(storageKey, true)
          setOpen(false)
        }}
        className="mt-3 min-h-11 rounded-md bg-inzbc-tangerine px-4 py-2 text-sm font-semibold text-inzbc-navy transition-colors hover:bg-inzbc-tangerine/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
      >
        Got it
      </button>
    </section>
  )
}
