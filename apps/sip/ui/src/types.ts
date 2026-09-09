export type ScreenId =
  | 'overview'
  | 'brief-builder'
  | 'qa-review'
  | 'ceo-decision'
  | 'distribution-status'
  | 'runs-candidates'
  | 'fta'
  | 'comms'
  | 'member'

/** A nav group. The platform has four modules; SIP is the one with several screens. */
export interface ScreenGroup {
  label: string
  screens: { id: ScreenId; label: string }[]
}

// Grouped rather than flat because the shell now spans four modules, not one tool's four screens.
// A flat strip of nine tabs says nothing about which of them belong to the same pipeline; the
// grouping is the information a first-time viewer actually needs to read the system.
export const SCREEN_GROUPS: ScreenGroup[] = [
  {
    label: 'Platform',
    screens: [{ id: 'overview', label: 'Overview' }],
  },
  {
    label: 'Trade Intelligence',
    screens: [
      { id: 'runs-candidates', label: 'Runs & Candidates' },
      { id: 'brief-builder', label: 'Brief Builder' },
      { id: 'qa-review', label: 'QA Review' },
      { id: 'ceo-decision', label: 'CEO Decision' },
      { id: 'distribution-status', label: 'Distribution' },
    ],
  },
  {
    label: 'Member services',
    screens: [
      { id: 'fta', label: 'FTA Explainer' },
      { id: 'comms', label: 'Comms Assistant' },
      { id: 'member', label: 'Member Portal' },
    ],
  },
]

export const SCREENS: { id: ScreenId; label: string }[] = SCREEN_GROUPS.flatMap(
  (group) => group.screens,
)
