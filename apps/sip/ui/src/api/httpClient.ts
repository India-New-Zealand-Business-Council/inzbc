import { getCsrfToken } from './session'
/**
 * Shared fetch wrapper for `/api/runs` and `/api/candidates` — eleven endpoints across
 * runsClient.ts/candidatesClient.ts, all served by the same FastAPI app and the same error
 * shape, so the parsing lives once here rather than eleven times. Mirrors the typed-error
 * pattern in apps/fta/ui/src/api/client.ts and apps/comms/ui/src/api/client.ts, adapted for a
 * client with many endpoints instead of one.
 */

/**
 * services/api/hardening.py wraps every error response — validation failure, a raised
 * HTTPException, or an unhandled exception — in one envelope: `{error: {status, code,
 * message}}`. This is the one place that unwraps it.
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

export class SipApiError extends Error {
  /** HTTP status, when the failure reached the server (absent for a network/abort failure). */
  status?: number
  /** Machine-readable code from the error envelope, e.g. "http_error", "invalid_request". */
  code?: string

  constructor(message: string, options?: ErrorOptions & { status?: number; code?: string }) {
    super(message, options)
    this.name = 'SipApiError'
    this.status = options?.status
    this.code = options?.code
  }
}

export type RequestOptions = { signal?: AbortSignal; baseUrl?: string }

/**
 * `POST /api/candidates/:id/verify` and `/score` return 403 for the exact same reason: the
 * verification gate (`apps/sip/collector/verification.py`) refused. Callers that want to show a
 * gate-specific message rather than a generic error can check this rather than parsing `.message`.
 */
export function isVerificationGateError(error: unknown): error is SipApiError {
  return error instanceof SipApiError && error.status === 403
}

/** True for the CAS failure on a run's `expected_version` — the caller's copy is stale. */
export function isConcurrentModificationError(error: unknown): error is SipApiError {
  return error instanceof SipApiError && error.status === 409
}

/**
 * Adds the CSRF token to a state-changing request, and leaves a read alone.
 *
 * `services/api/session.py`'s `write_access` refuses any non-GET with no `X-CSRF-Token` header, so
 * a client sending the cookie alone is authenticated and refused. `SameSite=Lax` still permits a
 * top-level cross-site POST, which is the shape of a form-submission CSRF, so the token is the
 * control rather than belt-and-braces.
 *
 * Reads deliberately do not fetch a session. Requiring a token on a GET would train callers to
 * send it everywhere, and would make every read depend on a second request it does not need.
 *
 * Done here rather than in each client so a new write cannot forget it. Four call sites needed it
 * and none had it; a fifth would have been the same.
 */
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])

async function withCsrfToken(url: string, init: RequestInit): Promise<RequestInit> {
  const method = (init.method ?? 'GET').toUpperCase()
  if (SAFE_METHODS.has(method)) return init

  // The same origin the request goes to, so a caller using `baseUrl` for a cross-origin
  // deployment reads its session from that host rather than from this page's.
  const baseUrl = url.slice(0, url.indexOf('/api/'))
  const csrfToken = await getCsrfToken(baseUrl)
  return { ...init, headers: { ...(init.headers as Record<string, string>), 'X-CSRF-Token': csrfToken } }
}

/**
 * Fetches `url`, parses the JSON body, and throws `SipApiError` for every failure mode: network
 * failure, non-JSON body, or a non-2xx response (using the server's own message when the error
 * envelope is present, falling back to a generic one otherwise). `AbortError` is rethrown as-is,
 * matching apps/fta/ui and apps/comms/ui, so a caller's own abort handling still works.
 */
export async function apiRequest<T>(url: string, init: RequestInit): Promise<T> {
  const request = await withCsrfToken(url, init)

  let response: Response
  try {
    response = await fetch(url, request)
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new SipApiError('Could not reach the SIP service.', { cause })
  }

  let body: unknown
  try {
    body = await response.json()
  } catch (cause) {
    if (response.ok) {
      throw new SipApiError('SIP service returned an unreadable response.', { cause })
    }
    throw new SipApiError(`SIP service returned ${response.status}.`, { status: response.status })
  }

  if (!response.ok) {
    if (isErrorEnvelope(body)) {
      throw new SipApiError(body.error.message, { status: body.error.status, code: body.error.code })
    }
    throw new SipApiError(`SIP service returned ${response.status}.`, { status: response.status })
  }

  return body as T
}

/**
 * For the UUID foreign keys this UI still takes as free-text input from the caller — e.g.
 * `duplicate_of` (`candidates.id`, `database/schema.sql`). `initiated_by`/`actor_id` no longer
 * need this: #278 moved them to session-derived identity, so no request model accepts them from
 * the client at all. What remains applies the same reasoning: the API accepts any string at the
 * schema level and only fails at the database, as a bare, unhelpful 500 (a non-UUID value fails
 * Postgres's type check before the foreign key is even reached). Checking the format client-side
 * turns that into a clear, immediate message instead of a round trip to a 500. It cannot confirm
 * the id belongs to a real row — there is no endpoint to check that against — only that it is
 * shaped like one.
 */
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function isUuid(value: string): boolean {
  return UUID_PATTERN.test(value.trim())
}
