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
 * Required properties of each response arm, mirrored from the OpenAPI `required` arrays.
 *
 * A test asserts these lists match `schemas/openapi.json` exactly, so the contract and this
 * runtime guard cannot drift apart silently. Without that pairing, a hand-maintained list is
 * just a second source of truth waiting to go stale.
 */
const ANSWER_REQUIRED = [
  'id', 'topic', 'sector', 'treatment', 'confirmed', 'citation', 'verified_at',
  'status_line', 'jurisdiction', 'next_step', 'disclaimer', 'confidence', 'confidence_meaning',
] as const

const ACTION_REQUIRED_REQUIRED = [
  'message', 'next_step', 'escalation_path', 'status_line', 'jurisdiction', 'disclaimer',
  'confidence', 'confidence_meaning',
] as const

export const REQUIRED_FIELDS = {
  AnswerOut: ANSWER_REQUIRED,
  ActionRequiredOut: ACTION_REQUIRED_REQUIRED,
} as const

function hasAllStrings(value: unknown, keys: readonly string[]): boolean {
  if (typeof value !== 'object' || value === null) return false
  const record = value as Record<string, unknown>
  return keys.every((key) => {
    const field = record[key]
    // `confirmed` is the one non-string required field.
    if (key === 'confirmed') return typeof field === 'boolean'
    return typeof field === 'string' && field.length > 0
  })
}

/**
 * Guards the invariants the UI depends on: the status tag agrees with the payload, and every
 * answer actually carries its evidence.
 *
 * A shallow check that only counted array length would accept `{answers: [{}]}` and the UI
 * would render `undefined` in place of the citation, confidence and disclaimer — presenting an
 * empty shell with the visual authority of a sourced finding. The server enforces this too;
 * this is the client refusing to trust a malformed envelope.
 */
function isFtaQueryResult(body: unknown): body is FtaQueryResult {
  if (typeof body !== 'object' || body === null) return false
  const candidate = body as Partial<FtaQueryResult>
  if (typeof candidate.query !== 'string') return false
  if (!Array.isArray(candidate.answers)) return false

  if (candidate.status === 'matched') {
    if (candidate.answers.length === 0 || candidate.action_required) return false
    return candidate.answers.every((answer) => hasAllStrings(answer, ANSWER_REQUIRED))
  }
  if (candidate.status === 'no_match') {
    if (candidate.answers.length > 0) return false
    return hasAllStrings(candidate.action_required, ACTION_REQUIRED_REQUIRED)
  }
  return false
}
