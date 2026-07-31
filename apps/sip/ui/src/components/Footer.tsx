// Contact + social links are sourced from the live inzbc.org/connect page
// (docs/client-answers.md D14/D18, apps/site/content/connect.md), not invented. Flickr is
// deliberately excluded — client-answers.md D18 flags it as "still linked on the live site,
// decide whether it carries over" and that call hasn't been made yet. Same component as
// apps/comms/ui/src/components/Footer.tsx (no shared package between the two apps yet — each
// app under apps/*/ui is an independent pnpm workspace package).
const SOCIAL_LINKS = [
  { label: 'X (Twitter)', href: 'https://twitter.com/inzbc' },
  { label: 'LinkedIn', href: 'https://linkedin.com/company/india-new-zealand-business-council' },
  { label: 'Facebook', href: 'https://facebook.com/inzbc' },
  { label: 'YouTube', href: 'https://youtube.com/channel/UC9MQW-VliLqOdT4GUktKfZQ' },
]

export function Footer() {
  return (
    <footer className="bg-inzbc-navy text-white">
      <div className="mx-auto max-w-4xl px-4 py-6 text-sm">
        <nav aria-label="Social media" className="flex flex-wrap gap-x-5 gap-y-2">
          {SOCIAL_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-sm underline decoration-white/40 underline-offset-2 transition-colors hover:text-inzbc-lavender hover:decoration-inzbc-lavender focus-visible:outline-inzbc-lavender"
            >
              {link.label}
            </a>
          ))}
        </nav>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/20 pt-4">
          <p>&copy; 2026 India New Zealand Business Council. All rights reserved.</p>
          <a
            href="mailto:sunil@inzbc.org"
            className="rounded-sm underline decoration-white/40 underline-offset-2 transition-colors hover:text-inzbc-lavender hover:decoration-inzbc-lavender focus-visible:outline-inzbc-lavender"
          >
            Contact us
          </a>
        </div>
      </div>
    </footer>
  )
}
