import { useId, useState } from 'react'
import { isUuid } from '../api/httpClient'
import {
  mergeCandidate,
  routeCandidate,
  scoreCandidate,
  SIGNAL_STRENGTHS,
  SipApiError,
  SOURCE_CONFIDENCES,
  verifyCandidate,
  VERIFICATION_STATES,
  type CandidateOut,
  type SignalStrength,
  type SourceConfidence,
  type VerificationState,
} from '../api/candidatesClient'

interface Props {
  candidate: CandidateOut
  /** UUID of the acting user — see RunsListScreen.tsx's Props doc for why this is caller-supplied. */
  actorId: string
  onUpdated: (updated: CandidateOut) => void
}

type ActionKind = 'verify' | 'score' | 'route' | 'merge'

type PanelState = { kind: 'idle' } | { kind: 'loading' } | { kind: 'error'; message: string }

const ACTION_PANEL_LABEL: Record<ActionKind, string> = {
  verify: 'Verify',
  score: 'Score',
  route: 'Route',
  merge: 'Merge',
}

/** 0-5 in `apps/sip/pipeline/models.py` (`Field(ge=0, le=5)`), not enforced by `ScoreIn` itself —
 * clamped here since the API will otherwise accept and store an out-of-range value unchanged. */
function clampScore(value: string): number | null {
  if (!value.trim()) return null
  const parsed = Math.round(Number(value))
  if (Number.isNaN(parsed)) return null
  return Math.min(5, Math.max(0, parsed))
}

/**
 * The four candidate commands (verify/score/route/merge), each with its own field set
 * (`services/api/candidates.py`'s `VerifyIn`/`ScoreIn`/`RouteIn`/`MergeIn`). Shared between
 * CandidatesListScreen and CandidateDetailScreen — unlike this app's other screens, which
 * deliberately inline their own JSX with no shared UI components, this form is substantial and
 * would otherwise be duplicated verbatim in both places, which is worse than one shared component
 * (same reasoning as lib/runActions.ts sharing logic between RunsListScreen/RunDetailScreen).
 */
export function CandidateActionPanel({ candidate, actorId, onUpdated }: Props) {
  const [openAction, setOpenAction] = useState<ActionKind | null>(null)
  const [reason, setReason] = useState('')
  const [verification, setVerification] = useState<VerificationState>('Verified')
  const [nzRelevance, setNzRelevance] = useState('')
  const [indiaRelevance, setIndiaRelevance] = useState('')
  const [memberRelevance, setMemberRelevance] = useState('')
  const [signal, setSignal] = useState<SignalStrength | ''>('')
  const [confidence, setConfidence] = useState<SourceConfidence | ''>('')
  const [proposedRouting, setProposedRouting] = useState('')
  const [included, setIncluded] = useState(false)
  const [duplicateOf, setDuplicateOf] = useState('')
  const [panelState, setPanelState] = useState<PanelState>({ kind: 'idle' })
  const formId = useId()

  function openPanel(action: ActionKind) {
    setOpenAction(openAction === action ? null : action)
    setReason('')
    setVerification('Verified')
    setNzRelevance('')
    setIndiaRelevance('')
    setMemberRelevance('')
    setSignal('')
    setConfidence('')
    setProposedRouting('')
    setIncluded(false)
    setDuplicateOf('')
    setPanelState({ kind: 'idle' })
  }

  async function submit(action: ActionKind) {
    if (!isUuid(actorId)) {
      setPanelState({ kind: 'error', message: 'Enter a valid "Acting as" user id above before taking any action.' })
      return
    }
    if (!reason.trim()) {
      setPanelState({ kind: 'error', message: 'A reason is required.' })
      return
    }
    if (action === 'merge' && !duplicateOf.trim()) {
      setPanelState({ kind: 'error', message: 'The duplicate-of candidate id is required.' })
      return
    }
    setPanelState({ kind: 'loading' })
    try {
      let updated: CandidateOut
      const common = { actor_id: actorId, reason: reason.trim() }
      if (action === 'verify') {
        updated = await verifyCandidate(candidate.id, { verification, ...common })
      } else if (action === 'score') {
        updated = await scoreCandidate(candidate.id, {
          nz_relevance: clampScore(nzRelevance),
          india_relevance: clampScore(indiaRelevance),
          member_relevance: clampScore(memberRelevance),
          signal: signal || null,
          confidence: confidence || null,
          ...common,
        })
      } else if (action === 'route') {
        updated = await routeCandidate(candidate.id, {
          proposed_routing: proposedRouting.trim() || null,
          included,
          ...common,
        })
      } else {
        updated = await mergeCandidate(candidate.id, { duplicate_of: duplicateOf.trim(), ...common })
      }
      setOpenAction(null)
      setPanelState({ kind: 'idle' })
      onUpdated(updated)
    } catch (error) {
      setPanelState({
        kind: 'error',
        message: error instanceof SipApiError ? error.message : 'Something went wrong. Please try again.',
      })
    }
  }

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {(Object.keys(ACTION_PANEL_LABEL) as ActionKind[]).map((action) => (
          <button
            key={action}
            type="button"
            aria-expanded={openAction === action}
            onClick={() => openPanel(action)}
            className="min-h-11 rounded-md border border-inzbc-navy/20 px-3 py-2 text-sm font-medium text-inzbc-navy transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
          >
            {ACTION_PANEL_LABEL[action]}
          </button>
        ))}
      </div>

      {openAction ? (
        <form
          className="mt-3 space-y-2 rounded-md border border-inzbc-navy/10 bg-slate-50 p-3"
          onSubmit={(event) => {
            event.preventDefault()
            void submit(openAction)
          }}
        >
          {openAction === 'verify' ? (
            <div>
              <label htmlFor={`${formId}-verification`} className="text-xs font-medium text-inzbc-navy">
                Verification
              </label>
              <select
                id={`${formId}-verification`}
                value={verification}
                onChange={(event) => setVerification(event.target.value as VerificationState)}
                className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
              >
                {VERIFICATION_STATES.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              {candidate.signal === 'High' || candidate.signal === 'Critical' ? (
                <p className="mt-1 text-xs text-slate-500">
                  This candidate&rsquo;s current signal is {candidate.signal} — anything other than
                  Verified or Partially Verified will be refused (verification gate).
                </p>
              ) : null}
            </div>
          ) : null}

          {openAction === 'score' ? (
            <>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                <div>
                  <label htmlFor={`${formId}-nz`} className="text-xs font-medium text-inzbc-navy">
                    NZ relevance (0-5)
                  </label>
                  <input
                    id={`${formId}-nz`}
                    type="number"
                    min={0}
                    max={5}
                    value={nzRelevance}
                    onChange={(event) => setNzRelevance(event.target.value)}
                    className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                  />
                </div>
                <div>
                  <label htmlFor={`${formId}-india`} className="text-xs font-medium text-inzbc-navy">
                    India relevance (0-5)
                  </label>
                  <input
                    id={`${formId}-india`}
                    type="number"
                    min={0}
                    max={5}
                    value={indiaRelevance}
                    onChange={(event) => setIndiaRelevance(event.target.value)}
                    className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                  />
                </div>
                <div>
                  <label htmlFor={`${formId}-member`} className="text-xs font-medium text-inzbc-navy">
                    Member relevance (0-5)
                  </label>
                  <input
                    id={`${formId}-member`}
                    type="number"
                    min={0}
                    max={5}
                    value={memberRelevance}
                    onChange={(event) => setMemberRelevance(event.target.value)}
                    className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <div>
                  <label htmlFor={`${formId}-signal`} className="text-xs font-medium text-inzbc-navy">
                    Signal
                  </label>
                  <select
                    id={`${formId}-signal`}
                    value={signal}
                    onChange={(event) => setSignal(event.target.value as SignalStrength | '')}
                    className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                  >
                    <option value="">Unchanged</option>
                    {SIGNAL_STRENGTHS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor={`${formId}-confidence`} className="text-xs font-medium text-inzbc-navy">
                    Source confidence
                  </label>
                  <select
                    id={`${formId}-confidence`}
                    value={confidence}
                    onChange={(event) => setConfidence(event.target.value as SourceConfidence | '')}
                    className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                  >
                    <option value="">Unchanged</option>
                    {SOURCE_CONFIDENCES.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              {(signal === 'High' || signal === 'Critical') &&
              candidate.verification !== 'Verified' &&
              candidate.verification !== 'Partially Verified' ? (
                <p className="text-xs text-slate-500">
                  This candidate is currently {candidate.verification} — {signal} signal will be
                  refused until it is Verified or Partially Verified (verification gate).
                </p>
              ) : null}
            </>
          ) : null}

          {openAction === 'route' ? (
            <>
              <div>
                <label htmlFor={`${formId}-routing`} className="text-xs font-medium text-inzbc-navy">
                  Proposed routing
                </label>
                <input
                  id={`${formId}-routing`}
                  type="text"
                  value={proposedRouting}
                  onChange={(event) => setProposedRouting(event.target.value)}
                  className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-inzbc-navy">
                <input type="checkbox" checked={included} onChange={(event) => setIncluded(event.target.checked)} />
                Include in the brief
              </label>
            </>
          ) : null}

          {openAction === 'merge' ? (
            <div>
              <label htmlFor={`${formId}-duplicate`} className="text-xs font-medium text-inzbc-navy">
                Duplicate of (candidate id)
              </label>
              <input
                id={`${formId}-duplicate`}
                type="text"
                value={duplicateOf}
                onChange={(event) => setDuplicateOf(event.target.value)}
                className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
              />
              <p className="mt-1 text-xs text-slate-500">Merging also removes this candidate from &ldquo;included&rdquo; findings.</p>
            </div>
          ) : null}

          <div>
            <label htmlFor={`${formId}-reason`} className="text-xs font-medium text-inzbc-navy">
              Reason
            </label>
            <input
              id={`${formId}-reason`}
              type="text"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              className="mt-1 w-full rounded-md border border-inzbc-navy/20 p-2 text-sm transition-colors hover:border-inzbc-navy/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inzbc-blue"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="submit"
              disabled={panelState.kind === 'loading'}
              className="min-h-11 rounded-md bg-inzbc-tangerine px-3 py-2 text-sm font-semibold text-inzbc-navy disabled:cursor-progress disabled:opacity-60"
            >
              {panelState.kind === 'loading' ? 'Submitting…' : `Confirm ${ACTION_PANEL_LABEL[openAction]}`}
            </button>
            <button type="button" onClick={() => openPanel(openAction)} className="min-h-11 px-2 text-sm font-medium text-inzbc-blue underline">
              Cancel
            </button>
          </div>
          {panelState.kind === 'error' ? (
            <p role="alert" className="text-sm text-inzbc-crimson">
              {panelState.message}
            </p>
          ) : null}
        </form>
      ) : null}
    </div>
  )
}
