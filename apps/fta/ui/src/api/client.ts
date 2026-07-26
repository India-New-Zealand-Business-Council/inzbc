import type { components } from './schema'

export type Answer = components['schemas']['AnswerOut']
export type ActionRequired = components['schemas']['ActionRequiredOut']

type Envelope = components['schemas']['FtaQueryResponse']

/**
 * The API's status-tagged envelope, narrowed into a true discriminated union.
 *
 * OpenAPI cannot express "action_required is present exactly when status is no_match", so the
 * generated type makes it nullable on both arms and a consumer needs a non-null assertion to
 * render it. Deriving the union here moves that guarantee into the compiler: narrowing on
 * `status === 'no_match'` yields a non-nullable `action_required`, and reading it on the matched
 * arm does not type-check.
 *
 * Derived from the generated `Envelope` rather than hand-written, so a schema change still breaks
 * this rather than silently drifting (ADR-0001).
 */
export type FtaQueryResult =
  | (Omit<Envelope, 'status' | 'action_required'> & {
      status: 'matched'
      action_required?: null
    })
  | (Omit<Envelope, 'status' | 'action_required'> & {
      status: 'no_match'
      action_required: ActionRequired
    })

export class FtaQueryError extends Error {}

export async function queryFta(
  q: string,
  options: { signal?: AbortSignal; baseUrl?: string } = {},
): Promise<FtaQueryResult> {
  const { signal, baseUrl = '' } = options
  const url = `${baseUrl}/api/fta/query?q=${encodeURIComponent(q)}`

  let response: Response
  try {
    response = await fetch(url, { signal, headers: { Accept: 'application/json' } })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new FtaQueryError('Could not reach the FTA service.', { cause })
  }

  if (!response.ok) {
    throw new FtaQueryError(`FTA service returned ${response.status}.`)
  }

  const body = (await response.json()) as unknown
  if (!isFtaQueryResult(body)) {
    throw new FtaQueryError('FTA service returned an unrecognised response.')
  }
  return body
}

/**
 * Guards the one invariant the UI depends on: the status tag and the payload agree. The server
 * enforces this too, but a UI that trusted a malformed envelope could render escalation guidance
 * as a sourced finding, which is the failure this whole path exists to prevent.
 */
function isFtaQueryResult(body: unknown): body is FtaQueryResult {
  if (typeof body !== 'object' || body === null) return false
  const candidate = body as Partial<FtaQueryResult>
  if (!Array.isArray(candidate.answers)) return false
  if (candidate.status === 'matched') {
    return candidate.answers.length > 0 && !candidate.action_required
  }
  if (candidate.status === 'no_match') {
    return candidate.answers.length === 0 && !!candidate.action_required
  }
  return false
}
