import { getCsrfToken } from './session'

export type ContentType = 'newsletter' | 'linkedin_post' | 'event_announcement' | 'member_spotlight'

export type Tone = 'formal' | 'warm' | 'concise'

/**
 * The structured brief (#303), replacing the single free-text `brief` field.
 *
 * The limits mirror the server's and are not decoration: the endpoint rejects a topic over 200
 * characters, a key point over 300, more than eight key points, more than five links, or a link
 * that is not a URL. Enforcing them here too is so the user finds out while typing rather than
 * from a 422.
 *
 * This is a reduction in what can be pasted, not a guarantee about content. A staff member can
 * still type a member's name into `topic`, which is why the server still declares the text as
 * staff-authored rather than claiming it has been minimised.
 */
export interface CommsDraftRequest {
  contentType: ContentType
  topic: string
  keyPoints?: string[]
  links?: string[]
  tone?: Tone
}

export const TOPIC_MAX_LENGTH = 200
export const KEY_POINT_MAX_LENGTH = 300
export const MAX_KEY_POINTS = 8
export const MAX_LINKS = 5

/**
 * Ceiling across topic, key points and links together — mirrors `TOTAL_BRIEF_BUDGET` in
 * `services/api/comms.py`.
 *
 * Per-field caps do not compose into a total. Summed, they allowed 12,940 characters, because a
 * URL can be ~2,000 and five are permitted — 3.2x the 4,000-character box #303 replaced. This is
 * the number that keeps the change a reduction rather than a rename.
 */
export const TOTAL_BRIEF_BUDGET = 4000

export interface CommsDraftResult {
  draft: string
}

export class CommsDraftError extends Error {}

/**
 * Calls the Comms Assistant drafting endpoint.
 *
 * `POST /api/comms/draft` is built and mounted (#53, PR #261), synchronous rather than SSE; the
 * streaming variant is still unbuilt work (#65).
 *
 * `credentials: 'same-origin'` because the Comms Assistant is a staff-only, same-origin surface
 * authenticated by session cookie (ADR-0004) — never a bearer token or API key from the browser
 * (NFR-01, `docs/api-integration-spec.md` "Cross-cutting rules").
 *
 * **The CSRF token is required, not optional.** The endpoint is behind `write_access`, which
 * refuses a state-changing request with no `X-CSRF-Token` header. Sending the cookie alone is
 * authenticated and refused, so this fetches the token first and every draft request carries it.
 * A `NotSignedInError` or `SessionUnavailableError` from that step propagates unchanged, because
 * "you are not signed in" needs a different answer from "the drafting service failed".
 */
export async function requestCommsDraft(
  { contentType, topic, keyPoints = [], links = [], tone = 'formal' }: CommsDraftRequest,
  options: { signal?: AbortSignal; baseUrl?: string } = {},
): Promise<CommsDraftResult> {
  const { signal, baseUrl = '' } = options
  const url = `${baseUrl}/api/comms/draft`

  const csrfToken = await getCsrfToken(baseUrl)

  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      signal,
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        'X-CSRF-Token': csrfToken,
      },
      // Empty key points and links are dropped rather than sent blank: the server caps the list
      // lengths, and padding them with empty strings spends that budget on nothing.
      body: JSON.stringify({
        content_type: contentType,
        topic,
        key_points: keyPoints.map((point) => point.trim()).filter(Boolean),
        links: links.map((link) => link.trim()).filter(Boolean),
        tone,
      }),
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
