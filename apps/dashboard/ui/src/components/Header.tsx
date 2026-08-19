import inzbcLogoAcronymWhite from '../assets/inzbc-logo-acronym-white.svg'

// Navy background + white text per INZBC Brand Guidelines 2026 v1.0 (Colour Palette, p.16),
// matching apps/comms/ui and apps/sip/ui headers.
export function Header() {
  return (
    <header className="bg-inzbc-navy text-white">
      <a
        href="#main-content"
        className="sr-only focus-visible:not-sr-only focus-visible:absolute focus-visible:left-4 focus-visible:top-4 focus-visible:z-50 focus-visible:rounded-md focus-visible:bg-white focus-visible:px-3 focus-visible:py-2 focus-visible:text-inzbc-navy"
      >
        Skip to main content
      </a>
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
        <a
          href="/"
          className="rounded-sm transition-opacity hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-lavender"
        >
          <img src={inzbcLogoAcronymWhite} alt="INZBC" className="h-6 w-auto" />
        </a>
        <nav aria-label="Primary">
          <span
            aria-current="page"
            className="border-b-2 border-inzbc-lavender text-sm font-medium text-white"
          >
            Executive Dashboard
          </span>
        </nav>
      </div>
    </header>
  )
}
