import inzbcLogoAcronymWhite from '../assets/inzbc-logo-acronym-white.svg'

// Navy background + white text per INZBC Brand Guidelines 2026 v1.0 (Colour Palette, p.16) — same
// treatment as apps/comms/ui's and apps/sip/ui's headers, so all three tools share one visual
// language. Logo: the acronym lockup, white variant, sourced from Drive (Brand/Logo Files/Export/
// SVG - Vector/INZBC_Logo_Acronym_White.svg), not fabricated — the guide (p.8) recommends it "at
// small scales, where 'India New Zealand Business Council' might become illegible," exactly this
// header's use case.
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
          className="rounded-sm transition-opacity hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lavender"
        >
          {/* Guide, p.11: acronym logo minimum size is 8mm / 25px wide — h-6 (24px tall) renders
              this ~81px wide at its native aspect ratio, comfortably above that floor. */}
          <img src={inzbcLogoAcronymWhite} alt="INZBC" className="h-6 w-auto" />
        </a>
        <nav aria-label="Primary">
          {/* Lavender, not Blue, for the current-page accent: the guide pairs Lavender with Navy
              (p.18) precisely because Blue #261866 on Navy #160933 is two dark colours with
              ~1.5:1 contrast — unreadable against this background, unlike on the light body where
              Blue is used for links. */}
          <span aria-current="page" className="border-b-2 border-inzbc-lavender text-sm font-medium text-white">
            FTA Explainer
          </span>
        </nav>
      </div>
    </header>
  )
}
