import type { components } from './schema'

export type Answer = components['schemas']['AnswerOut']
export type ActionRequired = components['schemas']['ActionRequiredOut']

/**
 * The API's status-tagged envelope. `status` is a discriminated union in the generated types,
 * so TypeScript refuses to compile a consumer that reads `action_required` without first
 * narrowing on `status` — a no-match cannot be silently dropped by checking `answers.length`.
 */
export type FtaQueryResult = components['schemas']['FtaQueryResponse']

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
