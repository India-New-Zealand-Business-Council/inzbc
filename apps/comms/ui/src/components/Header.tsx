// Navy background + white text per INZBC Brand Guidelines 2026 v1.0 (Colour Palette, p.16):
// Navy Blue #160933 is the brand's primary base, ~50% of colour use. Applied here via the
// --color-inzbc-navy token (src/index.css), not a raw hex, so it stays in sync with the rest
// of the app if the token ever changes.
//
// No INZBC logo asset (svg/png/jpg) exists in this repo yet — docs/design-decisions.md Open
// item #5. Rather than fabricate one, this renders the brand's own "acronym logo" concept from
// the guide (p.8: "best used at small scales, where 'India New Zealand Business Council' might
// become illegible") as a text wordmark. Swap for the real logo asset once INZBC supplies it.
export function Header() {
  return (
    <header className="bg-inzbc-navy text-white">
      <a
        href="#main-content"
        className="sr-only focus-visible:not-sr-only focus-visible:absolute focus-visible:left-4 focus-visible:top-4 focus-visible:z-50 focus-visible:rounded-md focus-visible:bg-white focus-visible:px-3 focus-visible:py-2 focus-visible:text-inzbc-navy"
      >
        Skip to main content
      </a>
      <div className="mx-auto flex max-w-2xl items-center justify-between px-4 py-4">
        <a
          href="/"
          className="rounded-sm font-[family-name:var(--font-heading)] text-lg font-bold uppercase tracking-wide text-white transition-colors hover:text-inzbc-lavender focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lavender"
        >
          INZBC
        </a>
        <nav aria-label="Primary">
          {/* Lavender, not Blue, for the current-page accent: the guide pairs Lavender with Navy
              (p.18, "Lavender > Blue > Navy Blue" is its featured gradient) precisely because
              Blue #261866 on Navy #160933 is two dark colours with ~1.5:1 contrast — unreadable
              against this background, unlike on the light body where Blue is used for links. */}
          <span
            aria-current="page"
            className="border-b-2 border-inzbc-lavender text-sm font-medium text-white"
          >
            Comms Assistant
          </span>
        </nav>
      </div>
    </header>
  )
}
