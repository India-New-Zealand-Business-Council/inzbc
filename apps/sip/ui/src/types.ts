export type ScreenId = 'brief-builder' | 'qa-review' | 'ceo-decision' | 'distribution-status'

export const SCREENS: { id: ScreenId; label: string }[] = [
  { id: 'brief-builder', label: 'Brief Builder' },
  { id: 'qa-review', label: 'QA Review' },
  { id: 'ceo-decision', label: 'CEO Decision' },
  { id: 'distribution-status', label: 'Distribution Status' },
]
