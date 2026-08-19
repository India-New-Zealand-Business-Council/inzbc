import { FtaQuery } from './components/FtaQuery'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import './index.css'

export function App() {
  return (
    // flex-col + flex-1 on main (not min-h-screen on main alone) so the footer sits at the
    // bottom of short pages without overlapping content on tall ones — the standard sticky-footer
    // layout, same as apps/comms/ui and apps/sip/ui.
    <div className="flex min-h-screen flex-col">
      <Header />
      <main id="main-content" className="flex-1 bg-slate-50">
        <div className="mx-auto max-w-2xl px-4 py-6 sm:py-8">
          {/* font-family/uppercase come from the h1 rule in index.css's @layer base; weight is
              bumped to Extrabold here since this is the single most prominent heading on the
              page — same treatment as apps/comms/ui's App.tsx. */}
          <h1 className="text-2xl font-extrabold text-inzbc-navy sm:text-3xl">INZBC FTA Explainer</h1>
          <p className="mt-2 text-slate-700">
            Ask about tariff outcomes under the New Zealand–India Free Trade Agreement. Answers are
            drawn from official sources; where INZBC cannot verify an answer, it says so.
          </p>
          <FtaQuery />
        </div>
      </main>
      <Footer />
    </div>
  )
}
