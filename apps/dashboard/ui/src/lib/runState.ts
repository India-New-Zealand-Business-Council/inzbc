// Same colour reasoning as apps/sip/ui/src/lib/runState.ts (Draft = neutral, healthy
// in-progress/completed = forest, needs-attention = tangerine, stopped = crimson). Not exhaustive
// of all 18 RunState values (schemas/state-machine.md) — states this dashboard doesn't have a
// bespoke treatment for fall back to the neutral badge.
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
