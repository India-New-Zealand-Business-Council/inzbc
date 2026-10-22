import type { components } from './schema'
import { apiRequest, type RequestOptions } from './httpClient'

export type DashboardOut = components['schemas']['DashboardOut']
export type OpenActionOut = components['schemas']['OpenActionOut']

export { DashboardApiError } from './httpClient'

/** `services/api/dashboard.py`'s single read endpoint: current run, coverage, gates, open actions. */
export async function getDashboard(options: RequestOptions = {}): Promise<DashboardOut> {
  const { signal, baseUrl = '' } = options
  return apiRequest<DashboardOut>(`${baseUrl}/api/dashboard`, {
    signal,
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  })
}
