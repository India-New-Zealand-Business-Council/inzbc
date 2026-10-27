import type { components } from './schema'
import { apiRequest, type RequestOptions } from './httpClient'

export type AuditEntryOut = components['schemas']['AuditEntryOut']
export type AuditPageOut = components['schemas']['AuditPageOut']

/** Read-only, run-scoped keyset paging. No unbounded audit export or client-side mutation. */
export async function listRunAudit(
  runId: string,
  beforeId?: number,
  options: RequestOptions = {},
): Promise<AuditPageOut> {
  const { signal, baseUrl = '' } = options
  const params = new URLSearchParams({ limit: '25' })
  if (beforeId !== undefined) params.set('before_id', String(beforeId))
  return apiRequest<AuditPageOut>(
    `${baseUrl}/api/runs/${encodeURIComponent(runId)}/audit?${params.toString()}`,
    { signal, credentials: 'same-origin', headers: { Accept: 'application/json' } },
  )
}
