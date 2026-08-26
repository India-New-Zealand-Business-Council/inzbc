// Navy/slate background = neutral/unstarted or terminal-closed, matching the "pending" treatment
// elsewhere in this app (QaReviewScreen's SECTION_CARD_CLASSES); forest = a healthy in-progress
// or completed state; tangerine = needs attention (paused, awaiting a decision); crimson =
// stopped. Not exhaustive of all 18 RunState values (schemas/state-machine.md) — states this UI's
// four actions never produce (Scanning, Report Drafted, etc.) fall back to the neutral badge
// rather than getting a bespoke colour for a state this UI cannot reach.
const STATE_BADGE_CLASSES: Record<string, string> = {
  Draft: 'bg-slate-100 text-slate-700',
  'Run Authorised': 'bg-inzbc-forest/10 text-inzbc-forest',
  'Coverage Locked': 'bg-inzbc-forest/10 text-inzbc-forest',
  'Awaiting CEO Decision': 'bg-inzbc-tangerine/20 text-inzbc-navy',
  Paused: 'bg-inzbc-tangerine/20 text-inzbc-navy',
  Stopped: 'bg-inzbc-crimson/10 text-inzbc-crimson',
  Distributed: 'bg-inzbc-forest/10 text-inzbc-forest',
  Closed: 'bg-slate-200 text-slate-700',
}

export function stateBadgeClass(state: string): string {
  return STATE_BADGE_CLASSES[state] ?? 'bg-slate-100 text-slate-700'
}
