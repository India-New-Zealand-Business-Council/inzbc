import { CommsAssistant } from './components/CommsAssistant'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import './index.css'

export function App() {
  return (
    // flex-col + flex-1 on main (not min-h-screen on main alone) so the footer sits at the
    // bottom of short pages without overlapping content on tall ones — the standard sticky-footer
    // layout, rather than main and footer independently guessing at page height.
    <div className="flex min-h-screen flex-col">
      <Header />
      {/* pt-24/pt-28 clears the fixed floating header (Header.tsx) — it no longer sits in
          normal flow, so the page has to make its own room for it. */}
      <main id="main-content" className="flex-1 bg-slate-50 pt-24 sm:pt-28">
        <div className="mx-auto max-w-2xl px-4 py-6 sm:py-8">
          {/* font-family/uppercase come from the h1 rule in index.css's @layer base; weight is
              bumped to Extrabold here — guide, p.20: "Medium/Extrabold when requiring different
              emphasis" — since this is the single most prominent heading on the page. */}
          <h1 className="text-2xl font-extrabold text-inzbc-navy sm:text-3xl">Comms Assistant</h1>
          <p className="mt-2 text-slate-700">
            Staff drafting helper for newsletters, event announcements, LinkedIn posts and member
            spotlights. Every draft needs a named human reviewer before it is sent or published
            (docs/modules/comms-assistant.md).
          </p>
          <CommsAssistant />
        </div>
      </main>
      <Footer />
    </div>
  )
}
