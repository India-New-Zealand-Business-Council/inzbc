// Same badge-colour reasoning as lib/runState.ts: forest = the "safe to act on" verification
// states, crimson = rejected, slate = neutral/not yet decided. Not required is treated as neutral
// rather than "safe" — apps/sip/collector/verification.py's gate never accepts it for a
// High/Critical signal, so badging it green would visually promise more than the gate allows.
const VERIFICATION_BADGE_CLASSES: Record<string, string> = {
  Verified: 'bg-inzbc-forest/10 text-inzbc-forest',
  'Partially Verified': 'bg-inzbc-forest/10 text-inzbc-forest',
  Unverified: 'bg-slate-100 text-slate-700',
  'Not Required': 'bg-slate-100 text-slate-700',
  Rejected: 'bg-inzbc-crimson/10 text-inzbc-crimson',
}

export function verificationBadgeClass(verification: string): string {
  return VERIFICATION_BADGE_CLASSES[verification] ?? 'bg-slate-100 text-slate-700'
}

// Crimson/tangerine for the two signal levels the verification gate actually cares about
// (apps/sip/collector/verification.py's _SIGNALS_REQUIRING_VERIFICATION), slate for the two that
// don't need prior verification — the colour doubles as a visual cue for "this one needs the gate
// checked before it can be set."
const SIGNAL_BADGE_CLASSES: Record<string, string> = {
  Critical: 'bg-inzbc-crimson/10 text-inzbc-crimson',
  High: 'bg-inzbc-tangerine/20 text-inzbc-navy',
  Medium: 'bg-slate-100 text-slate-700',
  Low: 'bg-slate-100 text-slate-700',
}

export function signalBadgeClass(signal: string | null): string {
  if (!signal) return 'bg-slate-100 text-slate-500'
  return SIGNAL_BADGE_CLASSES[signal] ?? 'bg-slate-100 text-slate-700'
}
