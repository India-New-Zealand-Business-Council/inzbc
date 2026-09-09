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
