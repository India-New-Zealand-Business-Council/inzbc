import type { components } from './schema'
import { apiRequest, type RequestOptions } from './httpClient'

export type CandidateOut = components['schemas']['CandidateOut']
export type VerificationState = components['schemas']['VerificationState']

export { DashboardApiError } from './httpClient'

/**
 * `run` is a required query param server-side (`services/api/candidates.py:list_candidates`) —
 * there is no all-runs listing, so callers always scope to one run (the current one, per
 * listRuns()[0]).
 */
export async function listCandidates(runId: string, options: RequestOptions = {}): Promise<CandidateOut[]> {
  const { signal, baseUrl = '' } = options
  return apiRequest<CandidateOut[]>(`${baseUrl}/api/candidates?run=${encodeURIComponent(runId)}`, {
    signal,
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  })
}
