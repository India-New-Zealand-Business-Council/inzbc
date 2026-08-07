# INZBC New Site — Design Direction (PROVISIONAL)

Shared working design file, deliberately tracked — Paras builds the design system from it.
**Order of authority: Sunil's brand asset guide > this file.**
Everything tagged `[[brand-guide]]` is a placeholder to be replaced by INZBC's real brand kit
when it arrives. UX/IA decisions below do not depend on brand colours and can proceed now.

## Who / what / one job
- **Product:** INZBC's public site — a bilateral (India–NZ) trade council since 1988.
- **Audience:** Ministers, diplomats, exporters, CEOs. Reads credibility and clarity, not flash.
- **The one job of the homepage:** make a serious business visitor trust INZBC and either join
  or engage (event, digest, contact) within one screen of scrolling.

## Tokens (provisional)
- **Accent:** one accent only, taken from the INZBC logo `[[brand-guide]]`. Not default blue.
- **Neutrals:** single hue family, warm-to-cool grey `[[brand-guide]]`; text at WCAG AA on white.
- **Type:** max two families (one for headings, one for text). Type scale ~1.25 ratio.
  Weight contrast over size contrast; slight negative letter-spacing on large headings only.
- **Spacing:** 4/8px scale. Generous whitespace. Max content width ~1100–1200px.
- **Radius:** one consistent radius, 8–12px. **Shadows:** layered low-opacity, no harsh borders.
- **Focus states:** always visible (diplomatic/gov audience = accessibility matters + expected).

## Don'ts (hard rules)
- No default blue; no more than two font families; no full-width paragraphs (cap line length).
- Never stack border + shadow + gradient on the same element.
- No overloaded mega-menu / content silos (the #1 failure mode for association sites).
- No invented brand colours, logos, stats, board names, or FTA figures.
- No AI-generic hero clichés ("Empowering X", abstract swooshes, stocky handshake photos).

## Information architecture (from UX research on trade bodies)
- **Top-level nav: 5–7 items max.** Proposed: About · Events · Trade · Members · Digest · News · Connect.
  FTA guide sits under Trade; keep the bar short, use a restrained dropdown for depth only.
- **Persistent "Join INZBC" CTA** in the header, visually distinct (accent), on every page —
  membership is the primary conversion and should never be more than one click away.
- Keep **sign-in / join / search outside** any dropdown, always reachable.
- **Homepage above the fold:** one-line positioning + Join CTA; a credibility strip
  (est. 1988, `[[member count]]`, recognised by both governments); then Events, latest Digest,
  Trade Resources.
- **Credibility signals near actions:** sponsor/partner logos (govt, banks, universities),
  recognised-by-both-governments line — placed where trust is decided (near Join and in footer).

## Build standards
- **Mobile-first** (~60% of traffic is mobile). Every layout designed at small width first.
- **WCAG 2.1 AA from day one** — contrast, keyboard nav, screen-reader labels. Non-negotiable
  for a government-adjacent audience.
- **Consistent branding across all pages** — no page should look like a different site.
- **Performance** — fast first load; compress imagery; a slow page loses this audience fast.

## Reference class (not to copy — to learn UX patterns from)
- Trade/association bodies and chambers: member-first nav, prominent Join call-out, event
  promotion integrated, clean resource organisation.
- Top-tier polish references (spacing, type, restraint) for execution quality, not aesthetics
  to clone: the INZBC look still comes from INZBC's brand kit.

## Open (resolve before final build)
- Replace all `[[brand-guide]]` tokens with Sunil's brand kit (logo, colours, fonts, imagery).
- Confirm his style references / any sites he likes (talking-points doc, point 1).
- Confirm final page list with INZBC.
