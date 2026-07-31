// Contact + social links are sourced from the live inzbc.org/connect page
// (docs/client-answers.md D14/D18, apps/site/content/connect.md), not invented. Flickr is
// deliberately excluded — client-answers.md D18 flags it as "still linked on the live site,
// decide whether it carries over" and that call hasn't been made yet.
const SOCIAL_LINKS = [
  { label: 'X (Twitter)', href: 'https://twitter.com/inzbc' },
  { label: 'LinkedIn', href: 'https://linkedin.com/company/india-new-zealand-business-council' },
  { label: 'Facebook', href: 'https://facebook.com/inzbc' },
  { label: 'YouTube', href: 'https://youtube.com/channel/UC9MQW-VliLqOdT4GUktKfZQ' },
]

export function Footer() {
  return (
    <footer className="bg-inzbc-navy text-white">
      <div className="mx-auto max-w-2xl px-4 py-6 text-sm">
        <nav aria-label="Social media" className="flex flex-wrap gap-x-5 gap-y-2">
          {SOCIAL_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              target="_blank"
              rel="noopener noreferrer"
              className="underline decoration-white/40 underline-offset-2"
            >
              {link.label}
            </a>
          ))}
        </nav>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/20 pt-4">
          <p>&copy; 2026 India New Zealand Business Council. All rights reserved.</p>
          <a href="mailto:sunil@inzbc.org" className="underline decoration-white/40 underline-offset-2">
            Contact us
          </a>
        </div>
      </div>
    </footer>
  )
}
