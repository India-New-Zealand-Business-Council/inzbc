/**
 * The session, and the CSRF token every write needs.
 *
 * Duplicated from `apps/comms/ui/src/api/session.ts` rather than shared. There is no shared
 * frontend package here and each app owns its own `src/api/`, so introducing one for two copies
 * of ninety lines would be a bigger change than the problem. Worth revisiting when a third app
 * needs it, or when either copy has to change.
 *
 * `services/api/session.py`'s `write_access` requires an `X-CSRF-Token` header on every
 * state-changing request and answers 403 without it. `SameSite=Lax` alone still permits a
 * top-level cross-site POST, which is the shape of a form-submission CSRF, so the token is the
 * control rather than belt-and-braces. A client that sends the cookie and omits the header is
 * authenticated and refused.
 *
 * The token is read from `GET /api/session`, which requires the cookie. Reading it that way is
 * what makes double-submit work: an attacker who can make the browser send the cookie still
 * cannot read the response to a same-origin request, so they cannot learn the token.
 */

export interface Session {
  userId: string
  name: string
  roles: string[]
  csrfToken: string
}

export class NotSignedInError extends Error {}
export class SessionUnavailableError extends Error {}

/**
 * The in-flight or resolved request, not the token.
 *
 * Caching the promise rather than the value means several writes firing at once share one request
 * instead of racing to fetch the same token. Caching the token would leave a window where the
 * second caller starts a second fetch because the first has not resolved yet.
 */
let inFlight: Promise<Session> | null = null

/** Forgets the cached session. For tests, and for a caller that has signed out. */
export function clearSession(): void {
  inFlight = null
}

/**
 * Supplies a session the caller already has, instead of fetching one.
 *
 * An app shell that has already called `GET /api/session` to decide which controls to show holds
 * everything this module would fetch. Handing it over avoids a second identical request on the
 * first write, and means the token the UI renders against is the token it writes with.
 *
 * Also what a component test uses: a test about a draft button should not have to know that the
 * client fetches a session first, and mocking a second endpoint in every such test is how a
 * suite ends up asserting the plumbing rather than the behaviour.
 */
export function seedSession(session: Session): void {
  inFlight = Promise.resolve(session)
}

/**
 * The current session, fetched once and reused.
 *
 * Throws `NotSignedInError` on 401 so a caller can tell "you are not signed in" from "the service
 * is broken". Those need different messages: one is fixed by signing in, the other is not.
 *
 * **A failed fetch is not cached.** An early failure would otherwise poison every later write for
 * the lifetime of the page, so the cache is cleared on the way out and the next caller retries.
 */
export function getSession(baseUrl = ''): Promise<Session> {
  inFlight ??= fetchSession(baseUrl).catch((error: unknown) => {
    inFlight = null
    throw error
  })
  return inFlight
}

/** The CSRF token for the current session. Convenience over `getSession`. */
export async function getCsrfToken(baseUrl = ''): Promise<string> {
  return (await getSession(baseUrl)).csrfToken
}

async function fetchSession(baseUrl: string): Promise<Session> {
  let response: Response
  try {
    response = await fetch(`${baseUrl}/api/session`, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    })
  } catch (cause) {
    throw new SessionUnavailableError('Could not reach the service to check your session.', {
      cause,
    })
  }

  if (response.status === 401) {
    throw new NotSignedInError('You are not signed in.')
  }
  if (!response.ok) {
    throw new SessionUnavailableError(`Checking your session returned ${response.status}.`)
  }

  let body: unknown
  try {
    body = await response.json()
  } catch (cause) {
    throw new SessionUnavailableError('The session response could not be read.', { cause })
  }
  if (!isSessionBody(body)) {
    throw new SessionUnavailableError('The session response was not in the expected shape.')
  }
  return {
    userId: body.user_id,
    name: body.name,
    roles: body.roles,
    csrfToken: body.csrf_token,
  }
}

interface SessionBody {
  user_id: string
  name: string
  roles: string[]
  csrf_token: string
}

/**
 * Checked rather than cast. An empty `csrf_token` would produce a request that fails the server's
 * `compare_digest` for a reason the caller cannot see, so a body missing it fails here with a
 * message that says what happened.
 */
function isSessionBody(value: unknown): value is SessionBody {
  if (typeof value !== 'object' || value === null) return false
  const body = value as Record<string, unknown>
  return (
    typeof body.user_id === 'string' &&
    typeof body.name === 'string' &&
    Array.isArray(body.roles) &&
    body.roles.every((role) => typeof role === 'string') &&
    typeof body.csrf_token === 'string' &&
    body.csrf_token.length > 0
  )
}
