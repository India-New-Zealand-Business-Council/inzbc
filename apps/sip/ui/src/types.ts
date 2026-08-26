export type ScreenId = 'brief-builder' | 'qa-review' | 'ceo-decision' | 'distribution-status' | 'runs-candidates'

export const SCREENS: { id: ScreenId; label: string }[] = [
  { id: 'brief-builder', label: 'Brief Builder' },
  { id: 'qa-review', label: 'QA Review' },
  { id: 'ceo-decision', label: 'CEO Decision' },
  { id: 'distribution-status', label: 'Distribution Status' },
  // Real, DB-backed runs/candidates data (#237, #242) — a separate screen from the four above,
  // which are still fixture-backed pending the report/dashboard endpoints (issue #44). See
  // screens/RunsCandidatesScreen.tsx.
  { id: 'runs-candidates', label: 'Runs & Candidates' },
]
