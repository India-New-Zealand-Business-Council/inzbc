/**
 * Shared fetch wrapper for the dashboard's read-only calls to `/api/runs` and `/api/candidates`.
 * Mirrors apps/sip/ui/src/api/httpClient.ts's typed-error pattern (same FastAPI service, same
 * `hardening.py` error envelope) trimmed to what a read-only dashboard needs — no mutation-only
 * error helpers like isVerificationGateError/isConcurrentModificationError.
 */

interface ErrorEnvelope {
  error: { status: number; code: string; message: string }
}

function isErrorEnvelope(body: unknown): body is ErrorEnvelope {
  if (typeof body !== 'object' || body === null) return false
  const err = (body as Record<string, unknown>).error
  if (typeof err !== 'object' || err === null) return false
  const e = err as Record<string, unknown>
  return typeof e.status === 'number' && typeof e.code === 'string' && typeof e.message === 'string'
}

export class DashboardApiError extends Error {
  /** HTTP status, when the failure reached the server (absent for a network/abort failure). */
  status?: number
  /** Machine-readable code from the error envelope, e.g. "http_error", "invalid_request". */
  code?: string

  constructor(message: string, options?: ErrorOptions & { status?: number; code?: string }) {
    super(message, options)
    this.name = 'DashboardApiError'
    this.status = options?.status
    this.code = options?.code
  }
}

export type RequestOptions = { signal?: AbortSignal; baseUrl?: string }

/**
 * Fetches `url`, parses the JSON body, and throws `DashboardApiError` for every failure mode:
 * network failure, non-JSON body, or a non-2xx response (using the server's own message when the
 * error envelope is present, falling back to a generic one otherwise). `AbortError` is rethrown
 * as-is so a caller's own abort handling still works.
 */
export async function apiRequest<T>(url: string, init: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(url, init)
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new DashboardApiError('Could not reach the SIP service.', { cause })
  }

  let body: unknown
  try {
    body = await response.json()
  } catch (cause) {
    if (response.ok) {
      throw new DashboardApiError('SIP service returned an unreadable response.', { cause })
    }
    throw new DashboardApiError(`SIP service returned ${response.status}.`, { status: response.status })
  }

  if (!response.ok) {
    if (isErrorEnvelope(body)) {
      throw new DashboardApiError(body.error.message, { status: body.error.status, code: body.error.code })
    }
    throw new DashboardApiError(`SIP service returned ${response.status}.`, { status: response.status })
  }

  return body as T
}
