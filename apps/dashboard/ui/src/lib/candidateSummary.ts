import type { CandidateOut, VerificationState } from '../api/candidatesClient'

export const VERIFICATION_STATES: VerificationState[] = [
  'Verified',
  'Partially Verified',
  'Unverified',
  'Not Required',
  'Rejected',
]

export interface CandidateSummary {
  total: number
  included: number
  byVerification: Record<VerificationState, number>
}

/**
 * Aggregates a run's candidates for the "coverage summary" panel — counts only, no per-candidate
 * detail, since that already exists in apps/sip/ui's Runs & Candidates review screen (#263).
 */
export function summarizeCandidates(candidates: CandidateOut[]): CandidateSummary {
  const byVerification = Object.fromEntries(
    VERIFICATION_STATES.map((state) => [state, 0]),
  ) as Record<VerificationState, number>

  let included = 0
  for (const candidate of candidates) {
    // CandidateOut.verification is typed `string` in the generated schema (the OpenAPI schema
    // doesn't declare it as an enum, unlike the standalone VerificationState schema) — the
    // backend only ever writes one of VERIFICATION_STATES (services/api/candidates.py), so this
    // cast is safe in practice even though the type doesn't prove it.
    const verification = candidate.verification as VerificationState
    byVerification[verification] += 1
    if (candidate.included) included += 1
  }

  return { total: candidates.length, included, byVerification }
}
