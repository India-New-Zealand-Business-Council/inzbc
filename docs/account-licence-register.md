# Account, licence and vendor register

Every external account and paid service the platform or the website depends on, who owns it, and
what breaks without it. Credentials themselves are in
[`secrets-register.md`](./secrets-register.md); this file is about the accounts behind them.

It exists for BR11: INZBC holds organisational ownership of every account, domain, social account
and credential. The failure this prevents is the ordinary one, where a system quietly depends on a
personal account belonging to someone who leaves in sixteen weeks.

**Status of the cost column.** Zero cost for this engagement is confirmed by the Executive Sponsor
(9 August 2026). Figures marked `[[to confirm]]` are subscriptions INZBC already held before the
engagement, and the team has not seen an invoice for them. They are recorded as unknown rather than
estimated.

## Accounts

| Service | Used for | Owner | Cost | Breaks without it |
|---|---|---|---|---|
| **GitHub** (`India-New-Zealand-Business-Council`) | Source, CI, project board, four repositories | INZBC organisation | Free tier | All development and CI |
| **Wix Vibe** | The public website: hosting, CMS, forms, media | Executive Sponsor | `[[to confirm]]` | The website. Note the site cannot be published by anyone else: publishing is a button in the Vibe editor and there is no API |
| **inzbc.org domain** | The public address | Executive Sponsor | `[[to confirm]]` | The public address. Cutover depends on it |
| **Member Jungle** | Membership system of record | INZBC | `[[to confirm]]` | Membership. The site links out; no data is duplicated, so the register is only there |
| **Zoho Backstage** | Event registration | INZBC | `[[to confirm]]` | Event registration. Event pages link out |
| **EmailOctopus** | Newsletters and the newsletter archive | INZBC | `[[to confirm]]` | The newsletter archive link. SIP does not send through it during this engagement |
| **OpenAI** | The model gateway, one credential | INZBC-held per the Executive Sponsor | Usage-based, the one genuine running cost | The FTA Explainer and Comms Assistant. Both fail closed rather than degrading |
| **Render** | Free-tier hosting for the FTA slice | `[[to confirm]]` | Free tier | The deployed slice. Nothing in the repository depends on it |
| **NewsAPI** | Collector source | INZBC | `[[to confirm]]` | One collection source. The collector records the failure rather than skipping silently |

## Overlaps worth a decision

**Zoho Backstage and Member Jungle both do events.** Member Jungle includes event functions and
INZBC also pays for Zoho Backstage. Nobody has established whether both are needed. This is #192,
and it is a live subscription cost rather than a design question.

**Wix Vibe and the platform are two hosting bills** if the platform ever leaves the free tier.
ADR-0007 keeps them separate deliberately: the website runs on Vibe, the staff tools run on the
platform's own origin, because the session cookie is host-only and cannot cross between them.

## What INZBC still owes

Nothing on this list is blocked on the team. Each is an account detail only INZBC holds:

- Confirmation of the cost lines marked `[[to confirm]]`
- Whether the Render account is INZBC-owned or currently sits with a team member
- Who at INZBC takes ownership of each account at handover, which is the open decision in the
  client approval document

## Handover check

Before sign-off, every row above must show an INZBC owner rather than an individual, and every
credential in `secrets-register.md` must be reachable by that owner. An account still tied to a
personal login at handover is the failure this register exists to catch, and it is easier to fix
now than in week sixteen.
