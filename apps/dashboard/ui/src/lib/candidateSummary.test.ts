import { describe, expect, it } from 'vitest'
import type { CandidateOut } from '../api/candidatesClient'
import { summarizeCandidates } from './candidateSummary'

function candidate(overrides: Partial<CandidateOut>): CandidateOut {
  return {
    id: 'c1',
    run_id: 'r1',
    headline: 'headline',
    source_id: null,
    url: null,
    summary: null,
    published_at: null,
    captured_at: '2026-01-01T00:00:00Z',
    in_coverage_window: true,
    nz_relevance: null,
    india_relevance: null,
    member_relevance: null,
    signal: null,
    confidence: null,
    verification: 'Unverified',
    duplicate_of: null,
    included: false,
    reason: null,
    proposed_routing: null,
    ...overrides,
  }
}

describe('summarizeCandidates', () => {
  it('returns all-zero counts for an empty list', () => {
    expect(summarizeCandidates([])).toEqual({
      total: 0,
      included: 0,
      byVerification: {
        Verified: 0,
        'Partially Verified': 0,
        Unverified: 0,
        'Not Required': 0,
        Rejected: 0,
      },
    })
  })

  it('counts total, included, and per-verification-state totals', () => {
    const candidates = [
      candidate({ id: 'a', verification: 'Verified', included: true }),
      candidate({ id: 'b', verification: 'Verified', included: false }),
      candidate({ id: 'c', verification: 'Unverified', included: false }),
      candidate({ id: 'd', verification: 'Rejected', included: false }),
    ]

    const summary = summarizeCandidates(candidates)

    expect(summary.total).toBe(4)
    expect(summary.included).toBe(1)
    expect(summary.byVerification.Verified).toBe(2)
    expect(summary.byVerification.Unverified).toBe(1)
    expect(summary.byVerification.Rejected).toBe(1)
    expect(summary.byVerification['Partially Verified']).toBe(0)
  })
})
