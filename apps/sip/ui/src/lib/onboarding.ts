/**
 * Whether this browser has seen the Getting Started screen.
 *
 * A per-viewer convenience only, so it lives in `localStorage`, and every access is guarded:
 * storage can be blocked or cleared (a private window, a locked-down browser). When it is, the
 * shell treats the visit as a first one and shows Getting Started, which costs one click.
 */
const KEY = 'inzbc.platform.onboarded.v1'

export function hasOnboarded(): boolean {
  try {
    return window.localStorage.getItem(KEY) === 'yes'
  } catch {
    return false
  }
}

export function markOnboarded(): void {
  try {
    window.localStorage.setItem(KEY, 'yes')
  } catch {
    // Nothing to do: the next visit shows Getting Started again.
  }
}

export function resetOnboarding(): void {
  try {
    window.localStorage.removeItem(KEY)
  } catch {
    // As above.
  }
}
