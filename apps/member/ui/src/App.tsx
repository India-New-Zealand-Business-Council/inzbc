import { Container } from './components/Container'
import { EventsSection } from './components/EventsSection'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { MembershipSection } from './components/MembershipSection'
import { NotificationsSection } from './components/NotificationsSection'
import { ResourcesSection } from './components/ResourcesSection'
import { Dashboard } from './pages/Dashboard'
import './index.css'

export function App() {
  return (
    // flex-col + flex-1 on main (not min-h-screen on main alone) so the footer sits at the
    // bottom of short pages without overlapping content on tall ones — same sticky-footer layout
    // as apps/comms/ui and apps/fta/ui.
    <div className="flex min-h-screen flex-col">
      <Header />
      {/* tabIndex=-1: a plain <main> isn't in the browser's focusable-elements set, so activating
          Header's "Skip to main content" link would scroll here without moving keyboard/AT focus
          — the next Tab press would carry on from wherever focus was before, defeating the skip
          link (WCAG technique G1/H69). */}
      <main id="main-content" tabIndex={-1} className="flex-1 bg-slate-50 focus:outline-none">
        <Container className="py-6 sm:py-8">
          <h1 className="text-2xl font-extrabold text-inzbc-navy sm:text-3xl">Member Portal</h1>
          {/* Per docs/modules/member-portal-spec.md's build gate: membership status, renewal,
              invoices, directory and login stay on Member Jungle until the retain/integrate/
              replace assessment is approved. This portal links out to Member Jungle for those
              rather than duplicating them — see CLAUDE.md's "one system of record" rule. */}
          {/* slate-800, not -700: -700 already clears 4.5:1 on this background, but the
              300-weight Merriweather body face reads faint at that shade — darker ink keeps the
              legibility margin the light weight needs. */}
          <p className="mt-2 text-slate-800">
            Membership, billing and the member directory are managed on Member Jungle. This portal
            links out to Member Jungle for those rather than holding membership data itself.
          </p>

          <Dashboard />

          <NotificationsSection />
          <MembershipSection />
          <EventsSection />
          <ResourcesSection />
        </Container>
      </main>
      <Footer />
    </div>
  )
}
