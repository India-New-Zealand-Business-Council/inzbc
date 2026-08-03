import { EventsSection } from './components/EventsSection'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import './index.css'

export function App() {
  return (
    // flex-col + flex-1 on main (not min-h-screen on main alone) so the footer sits at the
    // bottom of short pages without overlapping content on tall ones — same sticky-footer layout
    // as apps/comms/ui and apps/fta/ui.
    <div className="flex min-h-screen flex-col">
      <Header />
      <main id="main-content" className="flex-1 bg-slate-50">
        <div className="mx-auto max-w-2xl px-4 py-6 sm:py-8">
          <h1 className="text-2xl font-extrabold text-inzbc-navy sm:text-3xl">Member Portal</h1>
          {/* Per docs/modules/member-portal-spec.md's build gate: membership status, renewal,
              invoices, directory and login stay on Member Jungle until the retain/integrate/
              replace assessment is approved. This portal links out to Member Jungle for those
              rather than duplicating them — see CLAUDE.md's "one system of record" rule. */}
          <p className="mt-2 text-slate-700">
            Membership, billing and the member directory are managed on Member Jungle. This portal
            links out to Member Jungle for those rather than holding membership data itself.
          </p>

          <EventsSection />
        </div>
      </main>
      <Footer />
    </div>
  )
}
