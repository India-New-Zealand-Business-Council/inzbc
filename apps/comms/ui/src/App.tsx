import { CommsAssistant } from './components/CommsAssistant'
import { Header } from './components/Header'
import './index.css'

export function App() {
  return (
    <>
      <Header />
      <main id="main-content" className="min-h-screen bg-slate-50">
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
    </>
  )
}
