import { useCallback, useEffect, useRef, useState } from 'react'
import { listRunAudit, type AuditEntryOut } from '../api/auditClient'
import { SipApiError } from '../api/httpClient'

interface Props { runId: string }

type View =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'loaded'; entries: AuditEntryOut[]; cursor: number | null; loadingMore: boolean; loadError: string | null }

function displayDate(value: string): string {
  const timestamp = new Date(value)
  return Number.isNaN(timestamp.getTime()) ? 'Unknown timestamp' : timestamp.toLocaleString()
}

function errorMessage(error: unknown): string {
  return error instanceof SipApiError ? error.message : 'Could not load audit history. Try again.'
}

/**
 * Run-scoped audit metadata. The endpoint returns reason, old_value and new_value, but
 * this viewer deliberately does NOT render them: unbounded operator prose could contain
 * private information and the staff-read role is broader than confidential-detail access.
 * No approval or edit controls exist in this component.
 */
export function RunAuditHistory({ runId }: Props) {
  const [view, setView] = useState<View>({ kind: 'loading' })
  const inFlight = useRef<AbortController | null>(null)

  const fetchAudit = useCallback((beforeId?: number) => {
    inFlight.current?.abort()
    const controller = new AbortController()
    inFlight.current = controller
    listRunAudit(runId, beforeId, { signal: controller.signal })
      .then((page) => {
        if (controller.signal.aborted) return
        setView((previous) => ({
          kind: 'loaded',
          entries: beforeId !== undefined && previous.kind === 'loaded'
            ? [...previous.entries, ...page.entries]
            : page.entries,
          cursor: page.next_before_id,
          loadingMore: false,
          loadError: null,
        }))
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        if (beforeId !== undefined) {
          setView((previous) => previous.kind === 'loaded'
            ? { ...previous, loadingMore: false, loadError: errorMessage(error) }
            : { kind: 'error', message: errorMessage(error) })
        } else {
          setView({ kind: 'error', message: errorMessage(error) })
        }
      })
  }, [runId])

  useEffect(() => {
    fetchAudit()
    return () => inFlight.current?.abort()
  }, [fetchAudit])

  function refresh() {
    setView({ kind: 'loading' })
    fetchAudit()
  }

  function loadOlder() {
    if (view.kind !== 'loaded' || view.cursor === null || view.loadingMore) return
    const cursor = view.cursor
    setView({ ...view, loadingMore: true, loadError: null })
    fetchAudit(cursor)
  }

  return (
    <section aria-label="Run audit history" className="rounded-md border border-inzbc-navy/10 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-base font-semibold text-inzbc-navy">Audit history</h4>
          <p className="mt-1 text-sm text-slate-600">
            Recorded actions for this run, newest first. Metadata only; sensitive event values are not shown.
          </p>
        </div>
        <button type="button" onClick={refresh} disabled={view.kind === 'loading'}
          className="min-h-11 rounded-md border border-inzbc-navy/20 px-3 py-2 text-sm font-medium text-inzbc-navy disabled:opacity-60">
          Refresh audit
        </button>
      </div>

      {view.kind === 'loading' ? <p role="status" className="mt-3 text-sm">Loading audit history…</p> : null}
      {view.kind === 'error' ? <p role="alert" className="mt-3 text-sm text-inzbc-crimson">{view.message}</p> : null}
      {view.kind === 'loaded' && view.entries.length === 0
        ? <p className="mt-3 text-sm text-slate-600">No audit entries returned for this run.</p>
        : null}
      {view.kind === 'loaded' && view.entries.length > 0 ? (
        <ol aria-label="Recorded run actions" className="mt-3 space-y-2">
          {view.entries.map((entry) => (
            <li key={entry.id} className="rounded-md border border-inzbc-navy/10 p-3 text-sm">
              <div className="flex flex-wrap justify-between gap-2">
                <span className="font-medium text-inzbc-navy">{entry.action}</span>
                <span className="text-slate-600">{displayDate(entry.at)}</span>
              </div>
              <dl className="mt-1 grid grid-cols-1 gap-1 text-xs text-slate-600 sm:grid-cols-2">
                <div><dt className="inline font-medium">Event: </dt><dd className="inline">{entry.id}</dd></div>
                <div><dt className="inline font-medium">Actor: </dt><dd className="inline break-all">{entry.user_id ?? 'System'}</dd></div>
                <div><dt className="inline font-medium">Record type: </dt><dd className="inline">{entry.record_type ?? 'Not specified'}</dd></div>
                <div><dt className="inline font-medium">Record ID: </dt><dd className="inline break-all">{entry.record_id ?? 'Not specified'}</dd></div>
              </dl>
            </li>
          ))}
        </ol>
      ) : null}
      {view.kind === 'loaded' && view.loadError ? (
        <p role="alert" className="mt-2 text-sm text-inzbc-crimson">{view.loadError}</p>
      ) : null}
      {view.kind === 'loaded' && view.cursor !== null ? (
        <button type="button" onClick={loadOlder} disabled={view.loadingMore}
          className="mt-3 min-h-11 rounded-md border border-inzbc-navy/20 px-3 py-2 text-sm font-medium text-inzbc-navy disabled:opacity-60">
          {view.loadingMore ? 'Loading older entries…' : 'Load older entries'}
        </button>
      ) : null}
    </section>
  )
}
