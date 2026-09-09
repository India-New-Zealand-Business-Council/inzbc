import { apiRequest, type RequestOptions } from './httpClient'
import type { components } from './schema'

export type SourceLibraryOut = components['schemas']['SourceLibraryOut']

/**
 * `GET /api/source-library` — the SIP-185 mandatory source register.
 *
 * Fetched once and held as a lookup rather than resolved per candidate. A candidate carries
 * `source_id` and nothing else about its source, so a screen listing twelve of them would
 * otherwise make twelve requests to render twelve labels.
 */
export async function listSourceLibrary(
  options: RequestOptions = {},
): Promise<SourceLibraryOut[]> {
  return apiRequest<SourceLibraryOut[]>('/api/source-library', options)
}

/** `source_id` to its SIP-185 code and name, for screens that render a candidate's source. */
export async function sourceLookup(
  options: RequestOptions = {},
): Promise<Map<string, SourceLibraryOut>> {
  const sources = await listSourceLibrary(options)
  return new Map(sources.map((source) => [source.id, source]))
}

export type SourceCheckOut = components['schemas']['SourceCheckOut']

/**
 * `GET /api/runs/{id}/source-checks` — what was recorded against each mandatory source for a run.
 *
 * SIP-184 §4 makes this the coverage evidence QA checks: a mandatory source with no recorded
 * outcome is a Critical stop, not a warning, so the difference between "no outcome" and "an
 * outcome of Inaccessible" is the difference between a blocked run and a documented one.
 */
export async function listSourceChecks(
  runId: string,
  options: RequestOptions = {},
): Promise<SourceCheckOut[]> {
  return apiRequest<SourceCheckOut[]>(
    `/api/runs/${encodeURIComponent(runId)}/source-checks`,
    options,
  )
}
