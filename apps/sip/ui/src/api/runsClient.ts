import type { components } from './schema'
import { apiRequest, type RequestOptions } from './httpClient'

export type RunOut = components['schemas']['RunOut']
export type CreateRunIn = components['schemas']['CreateRunIn']
export type TransitionIn = components['schemas']['TransitionIn']

export { SipApiError, isConcurrentModificationError, isUuid } from './httpClient'

const JSON_HEADERS = { 'Content-Type': 'application/json', Accept: 'application/json' } as const

export async function listRuns(options: RequestOptions = {}): Promise<RunOut[]> {
  const { signal, baseUrl = '' } = options
  return apiRequest<RunOut[]>(`${baseUrl}/api/runs`, {
    signal,
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  })
}

export async function getRun(runId: string, options: RequestOptions = {}): Promise<RunOut> {
  const { signal, baseUrl = '' } = options
  return apiRequest<RunOut>(`${baseUrl}/api/runs/${encodeURIComponent(runId)}`, {
    signal,
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  })
}

export async function createRun(body: CreateRunIn, options: RequestOptions = {}): Promise<RunOut> {
  const { signal, baseUrl = '' } = options
  return apiRequest<RunOut>(`${baseUrl}/api/runs`, {
    method: 'POST',
    signal,
    credentials: 'same-origin',
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  })
}

/**
 * `start`/`pause`/`resume`/`complete` share one request/response shape and differ only in the
 * path segment and which state-machine edge the server applies (`services/api/runs.py`) — one
 * function parameterised by action, rather than four copies of the same body.
 */
async function transitionRun(
  action: 'start' | 'pause' | 'resume' | 'complete',
  runId: string,
  body: TransitionIn,
  options: RequestOptions,
): Promise<RunOut> {
  const { signal, baseUrl = '' } = options
  return apiRequest<RunOut>(`${baseUrl}/api/runs/${encodeURIComponent(runId)}/${action}`, {
    method: 'POST',
    signal,
    credentials: 'same-origin',
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  })
}

/** Draft -> Run Authorised. Human-gated; `approval_ref` only checked for presence (#227). */
export const startRun = (runId: string, body: TransitionIn, options: RequestOptions = {}): Promise<RunOut> =>
  transitionRun('start', runId, body, options)

/** Awaiting CEO Decision -> Paused. Human-gated; `approval_ref` must name a real `decision_records` row. */
export const pauseRun = (runId: string, body: TransitionIn, options: RequestOptions = {}): Promise<RunOut> =>
  transitionRun('pause', runId, body, options)

/** Paused -> Coverage Locked. Human-gated; `approval_ref` only checked for presence (#227). */
export const resumeRun = (runId: string, body: TransitionIn, options: RequestOptions = {}): Promise<RunOut> =>
  transitionRun('resume', runId, body, options)

/** Distributed -> Closed. Mechanical closeout, not human-gated — `approval_ref` is ignored. */
export const completeRun = (runId: string, body: TransitionIn, options: RequestOptions = {}): Promise<RunOut> =>
  transitionRun('complete', runId, body, options)

/**
 * Which lifecycle action, if any, is legal from a run's current state — drives which buttons a
 * screen enables. Mirrors the one edge each endpoint applies (`services/api/runs.py`'s module
 * docstring); the server is still the actual enforcer (`apps.sip.core.orchestrator`), this only
 * avoids offering a button that would 400.
 */
export function nextAction(state: string): 'start' | 'pause' | 'resume' | 'complete' | null {
  switch (state) {
    case 'Draft':
      return 'start'
    case 'Awaiting CEO Decision':
      return 'pause'
    case 'Paused':
      return 'resume'
    case 'Distributed':
      return 'complete'
    default:
      return null
  }
}
