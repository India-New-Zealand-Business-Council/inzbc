import type { components } from './schema'
import { apiRequest, type RequestOptions } from './httpClient'

export type CandidateOut = components['schemas']['CandidateOut']
export type CaptureCandidateIn = components['schemas']['CaptureCandidateIn']
export type VerifyIn = components['schemas']['VerifyIn']
export type ScoreIn = components['schemas']['ScoreIn']
export type RouteIn = components['schemas']['RouteIn']
export type MergeIn = components['schemas']['MergeIn']
export type VerificationState = components['schemas']['VerificationState']
export type SignalStrength = components['schemas']['SignalStrength']
export type SourceConfidence = components['schemas']['SourceConfidence']

export { SipApiError, isVerificationGateError, isUuid } from './httpClient'

export const VERIFICATION_STATES: VerificationState[] = [
  'Verified',
  'Partially Verified',
  'Unverified',
  'Not Required',
  'Rejected',
]

export const SIGNAL_STRENGTHS: SignalStrength[] = ['Low', 'Medium', 'High', 'Critical']

export const SOURCE_CONFIDENCES: SourceConfidence[] = ['High', 'Medium', 'Low', 'Unverified']

/** `apps/sip/collector/verification.py`'s allowlist — signals below need no prior verification. */
export const SIGNALS_REQUIRING_VERIFICATION: SignalStrength[] = ['High', 'Critical']

/** Same allowlist, the other side: verification states that satisfy a High/Critical signal. */
export const VERIFIED_STATES: VerificationState[] = ['Verified', 'Partially Verified']

const JSON_HEADERS = { 'Content-Type': 'application/json', Accept: 'application/json' } as const

export async function listCandidates(runId: string, options: RequestOptions = {}): Promise<CandidateOut[]> {
  const { signal, baseUrl = '' } = options
  return apiRequest<CandidateOut[]>(`${baseUrl}/api/candidates?run=${encodeURIComponent(runId)}`, {
    signal,
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  })
}

export async function getCandidate(candidateId: string, options: RequestOptions = {}): Promise<CandidateOut> {
  const { signal, baseUrl = '' } = options
  return apiRequest<CandidateOut>(`${baseUrl}/api/candidates/${encodeURIComponent(candidateId)}`, {
    signal,
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  })
}

export async function captureCandidate(
  body: CaptureCandidateIn,
  options: RequestOptions = {},
): Promise<CandidateOut> {
  const { signal, baseUrl = '' } = options
  return apiRequest<CandidateOut>(`${baseUrl}/api/candidates`, {
    method: 'POST',
    signal,
    credentials: 'same-origin',
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  })
}

function candidateCommand<TBody>(action: 'verify' | 'score' | 'route' | 'merge') {
  return (candidateId: string, body: TBody, options: RequestOptions = {}): Promise<CandidateOut> => {
    const { signal, baseUrl = '' } = options
    return apiRequest<CandidateOut>(
      `${baseUrl}/api/candidates/${encodeURIComponent(candidateId)}/${action}`,
      {
        method: 'POST',
        signal,
        credentials: 'same-origin',
        headers: JSON_HEADERS,
        body: JSON.stringify(body),
      },
    )
  }
}

/**
 * Sets `verification`. Rejects with a 403 (`isVerificationGateError`) if the candidate's
 * *current* `signal` is High/Critical and the incoming `verification` is not Verified/Partially
 * Verified — `apps/sip/collector/verification.py`'s gate, read in this direction by `/verify`.
 */
export const verifyCandidate = candidateCommand<VerifyIn>('verify')

/**
 * Sets relevance scores, `signal` and/or `confidence`. Rejects with a 403
 * (`isVerificationGateError`) if the incoming `signal` is High/Critical and the candidate's
 * *current* `verification` is not Verified/Partially Verified — the same gate, read in the other
 * direction by `/score`. Relevance scores are 0-5 in `apps/sip/pipeline/models.py` but that bound
 * is not enforced by this endpoint's request schema — callers must clamp client-side.
 */
export const scoreCandidate = candidateCommand<ScoreIn>('score')

/** Sets `proposed_routing`/`included`. No verification-gate interaction. */
export const routeCandidate = candidateCommand<RouteIn>('route')

/**
 * Marks this candidate as a duplicate of `duplicate_of`, which also forces `included = false` on
 * this candidate server-side — a duplicate cannot also count as a separate included finding.
 * Rejects with 400 for a self-merge, 404 if `duplicate_of` does not exist.
 */
export const mergeCandidate = candidateCommand<MergeIn>('merge')
