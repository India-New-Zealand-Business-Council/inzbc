import { Footer } from './components/Footer'
import { Header } from './components/Header'
import './index.css'

export function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main id="main-content" className="flex-1 bg-slate-50">
        <div className="mx-auto max-w-4xl px-4 py-6 sm:py-8">
          <h1 className="text-2xl font-extrabold text-inzbc-navy sm:text-3xl">
            Executive Dashboard
          </h1>
          <p className="mt-2 text-slate-700">
            SIP-only first slice (docs/modules/dashboards.md). Membership, Trade/FTA and Sponsors
            sections are not shown yet — the dashboards data layer (issue #47) hasn't been built.
          </p>
        </div>
      </main>
      <Footer />
    </div>
  )
}
