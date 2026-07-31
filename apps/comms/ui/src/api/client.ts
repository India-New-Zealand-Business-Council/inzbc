export type ContentType = 'newsletter' | 'linkedin_post' | 'event_announcement' | 'member_spotlight'

export interface CommsDraftRequest {
  contentType: ContentType
  brief: string
}

export interface CommsDraftResult {
  draft: string
}

export class CommsDraftError extends Error {}

/**
 * Calls the Comms Assistant drafting endpoint.
 *
 * `POST /api/comms/draft` is a **proposed** contract, not a built one: `services/api/main.py`
 * implements only the FTA Explainer read path today, and the Comms Assistant's own endpoint is
 * tracked as unbuilt work (`docs/workstreams/bhanu.md` issue #65, streaming SSE variant;
 * `docs/api-integration-spec.md` "What's specified but not built"). This client targets the
 * request/response shape that spec describes — content type + free-text brief in, a rendered
 * draft out — synchronous rather than SSE, matching what `ModelGateway.complete()` actually
 * offers server-side today. Calling this against a real deployment will 404 until the endpoint
 * lands; that is expected, not a bug in this client.
 *
 * `credentials: 'same-origin'` because the Comms Assistant is a staff-only, same-origin surface
 * authenticated by session cookie (ADR-0004) — never a bearer token or API key from the browser
 * (NFR-01, `docs/api-integration-spec.md` "Cross-cutting rules").
 */
export async function requestCommsDraft(
  { contentType, brief }: CommsDraftRequest,
  options: { signal?: AbortSignal; baseUrl?: string } = {},
): Promise<CommsDraftResult> {
  const { signal, baseUrl = '' } = options
  const url = `${baseUrl}/api/comms/draft`

  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      signal,
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ content_type: contentType, brief }),
    })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new CommsDraftError('Could not reach the Comms Assistant service.', { cause })
  }

  if (!response.ok) {
    throw new CommsDraftError(`Comms Assistant service returned ${response.status}.`)
  }

  let body: unknown
  try {
    body = await response.json()
  } catch (cause) {
    throw new CommsDraftError('Comms Assistant service returned an unreadable response.', { cause })
  }

  if (!isCommsDraftResult(body)) {
    throw new CommsDraftError('Comms Assistant service returned an unrecognised response.')
  }
  return body
}

/**
 * A shallow check that only confirmed `draft` was present would accept a body with no other
 * guardrails. There is no wider envelope to validate yet (unlike the FTA client's status-tagged
 * union) because the real contract isn't finalised — this guard covers the one field this UI
 * actually renders, so a malformed response fails closed instead of rendering `undefined` as if
 * it were a generated draft.
 */
function isCommsDraftResult(value: unknown): value is CommsDraftResult {
  if (typeof value !== 'object' || value === null) return false
  const draft = (value as Record<string, unknown>).draft
  return typeof draft === 'string' && draft.length > 0
}
