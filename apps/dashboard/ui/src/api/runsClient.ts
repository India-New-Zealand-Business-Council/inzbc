import type { components } from './schema'
import { apiRequest, type RequestOptions } from './httpClient'

export type RunOut = components['schemas']['RunOut']

export { DashboardApiError } from './httpClient'

/**
 * Every run, most recently created first (`services/api/persistence.py:list_runs` orders by
 * `created_at desc`) — `listRuns()[0]` is the current run, which is all the dashboard needs.
 */
export async function listRuns(options: RequestOptions = {}): Promise<RunOut[]> {
  const { signal, baseUrl = '' } = options
  return apiRequest<RunOut[]>(`${baseUrl}/api/runs`, {
    signal,
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  })
}
