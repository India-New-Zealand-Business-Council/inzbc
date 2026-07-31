import { CommsAssistant } from './components/CommsAssistant'
import { Header } from './components/Header'
import './index.css'

export function App() {
  return (
    <>
      <Header />
      <main id="main-content" className="min-h-screen bg-slate-50">
        <div className="mx-auto max-w-2xl px-4 py-6 sm:py-8">
          <h1 className="font-[family-name:var(--font-heading)] text-xl font-bold uppercase text-inzbc-navy sm:text-2xl">
            Comms Assistant
          </h1>
          <p className="mt-2 font-[family-name:var(--font-body)] text-slate-700">
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
