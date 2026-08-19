# Member portal — full specification

Detailed spec for the logged-in member experience, expanding
[`member-portal.md`](member-portal.md). Covers roles, login, dashboard screens, Member Jungle
integration points, and directory display. Where this doc and `member-portal.md` disagree,
`member-portal.md`'s "Open decisions" is the one still-open question — this doc doesn't silently
resolve it.

## Sources
- `docs/modules/member-portal.md` — module summary this expands.
- `docs/modules/membership-crm.md` — Member Jungle as provisional system of record, foundation
  decision, legal/privacy constraints.
- `docs/client-answers.md` §C — proposed (not confirmed) build decisions C1, C5, C6, C7, C8.
- `docs/discovery.md` — live-site audit of Join INZBC, Member Directory, Member Profiles.
- `docs/page-specs.md` §5 (Members) — directory embed-vs-link-out open item (OI-7).
- `docs/workstreams/bhanu.md` — the access-control Next Up item this doc flags a conflict against.
- `apps/site/content/members.md` — the page copy this portal sits behind.

## Two separate identity systems — do not conflate them

This matters enough to state before anything else. The platform has **two unrelated auth
systems**, and the member portal uses neither of the ones documented in most detail elsewhere:

1. **Internal staff auth** (SIP control API, Comms Assistant) — GitHub OAuth + an org-owned
   allowlist + Postgres-backed server-side sessions, per
   [ADR-0004](../decisions/0004-platform-graduation.md). Roles: SIP Owner, Analyst, Reviewer,
   Secretariat, Administrator, Board Viewer, Auditor (`database/schema.sql`, `roles` table). This
   is for the five-person internal team, not members.
2. **Member portal auth** — `[[proposed, pending INZBC confirmation]]`. `member-portal.md` proposes
   Wix Members Area with native Wix login ("Platform: Wix Members Area (login-gated)"), but nothing
   has confirmed it: `client-answers.md` C1, C5, C6 and C7 are all `PROPOSED`. Whatever is chosen,
   any roles it carries are member-side and a completely different set from the internal team's,
   on a completely different system.

**A real, unresolved tension worth surfacing:** `docs/workstreams/bhanu.md`'s Next Up list has
"Member portal access control: member roles + Members Area gating on the auth/RBAC model"
(SHARED-OK, taken from Paras). Everywhere else in this repo, "the auth/RBAC model" refers to
system 1 above (`roles`/`users`, GitHub OAuth) — but the member portal runs on Wix Members Area
(system 2), which Wix, not our Postgres `users` table, authenticates. Either that worklog line
means "gate Members Area content using role *names* that follow the same convention as system 1"
(naming parity, not a shared backend), or there's a real plan to route member auth through our
own auth system that isn't written down anywhere else. **Confirm with Bhanu before building
access control** — don't assume either reading.

## Member roles (Wix Members Area)

From `member-portal.md` §Roles: **Individual · Corporate · Strategic Partner · Sponsor · Board ·
Staff · Admin.**

Two things these roles are explicitly *not*, per the same source:
- Not the same as membership **category** (the fee tier a member pays for — see
  `docs/client-answers.md` D9, still `OPEN` for exact tiers).
- Not the same as **admin authority** (who can edit site/portal content) — that's a separate
  permission axis, brief §7.

## Login flow

**Not decided.** An earlier draft of this spec said login was decided as Wix Members Area
(native). Nothing decided it: `docs/client-answers.md` C1, C5, C6 and C7 are all `PROPOSED`,
including "no second membership register on the website" and "link to the Member Jungle directory,
do not copy or embed". `PROJECT-RULES.md` says to build only after the business rule is decided and not to
fill an unresolved rule with an assumption. Treat the login mechanism as
`[[proposed — pending INZBC confirmation]]`.

**Not decided — `member-portal.md`'s own open item:** single sign-on against Member Jungle
credentials (Option A) vs. a separate Wix login plus a distinct Member Jungle login for
billing/membership actions (Option B). Nothing in any sourced document picks one. What's
consistent with the sourced material so far:

- `docs/client-answers.md` C1 (proposed): Member Jungle stays the membership system of record,
  integrated, not replaced.
- C5 (proposed): the portal **links to** the Member Jungle directory rather than embedding a
  copy — "do not copy or embed a separate directory database."
- `discovery.md`: the live site's "Join Now" already redirects externally to
  `inzbc.memberjungle.club` — there is no existing pattern of Wix owning membership credentials.

Taken together this leans toward Option B (separate logins) being the path of least resistance,
but that's an inference, not a decision — `[[SSO vs separate login: confirm with Sunil/Bhanu
before building the login screen]]`.

**Working assumption for this spec, pending that confirmation:** a member logs into the Wix
Members Area to see the dashboard below; renewal, billing, and directory-record edits redirect
out to Member Jungle rather than being handled in-portal, consistent with C1/C5 and with how Join
already works.

## Dashboard screens

Directly from `member-portal.md`'s "Member sees" list, grouped into screens:

| Screen | Shows |
|---|---|
| **Dashboard home** | Membership status + renewal date/state; organisation/contact details summary |
| **Billing** | Invoices/receipts — read-only display; actual payment/renewal action redirects to Member Jungle (see Member Jungle integration points below) |
| **Resources** | Member-only reports & FTA sector briefings; event recordings & presentations |
| **Trade opportunities** | Delegation & trade opportunities; market-entry request form (both directions — see `docs/modules/sponsors-trade-services.md`); introduction request form |
| **Benefits** | Discounts & sponsor benefits available to the member |
| **Directory & consent** | The member's own directory listing preview; opt-in/opt-out controls for what appears in the public-facing Member Directory (see below) |
| **Corporate seats** *(Corporate membership only)* | Organisation record; primary + billing contact; authorised seats; add/remove/transfer a seat; directory consent per seat; continuity handling when a contact leaves the organisation |

**Request forms** on this dashboard (market-entry, introduction request) hand off to
`docs/forms-spec.md`'s common submission pattern (confirmation + owner notification + webhook) —
this doc doesn't re-specify form mechanics, only that these two request types originate here.

## Member Jungle integration points

Member Jungle (`inzbc.memberjungle.club`) is the **provisional system of record** for membership
(`membership-crm.md`) — the foundation decision to retain, integrate, or replace it is still
formally open (`client-answers.md` C1 is `PROPOSED`, not confirmed), even though every other
sourced document already assumes "retain and integrate."

What's sourced about the integration itself:

- **Directory:** link out to Member Jungle's directory; never copy/embed a second one (C5).
- **Join / renew:** external redirect to Member Jungle today (`discovery.md`); whether the portal
  gets a Member Jungle-linked "renew" button or a full redirect is the same Option A/B question as
  login above.
- **Event registration:** Member Jungle is the normal registration platform; Zoho is used only
  where a major event needs functions Member Jungle can't provide (C6, C7; also
  `apps/site/content/events.md`). The portal's "trade opportunities" screen should link to
  registration on whichever platform the event uses — it doesn't run registration itself.
- **Fee structure:** new tiers effective 1 Jan 2026, exact figures `OPEN` (`client-answers.md`
  D9) — **do not display placeholder or estimated pricing anywhere in the portal.**

**Not sourced anywhere — genuinely open:**
- The actual integration mechanism: does the portal call a Member Jungle API for status/read
  access, or is "linking out" purely a hyperlink with no data exchange at all? No API, webhook, or
  data-sync mechanism for Member Jungle is described in any document this spec draws on.
  `[[confirm with INZBC/Member Jungle: is there an API, and if so what does INZBC actually have
  access to]]`
- Whether the dashboard's "membership status + renewal" and "invoices/receipts" screens pull live
  data from Member Jungle or are placeholders until that mechanism exists.

## Member directory display

**Current live site** (`discovery.md` audit): alphabetical list, last updated 4 Nov 2024, no
search/filter, "contact secretariat if missing." `/member-directory` is a hidden page.

**New site — decision still open** (`page-specs.md` §5, OI-7): **embed/iframe the Member Jungle
directory** vs. **link out to it**. Nothing in the sourced material picks one; both are compatible
with C5's "don't duplicate the register" rule, since an embed can still read live from Member
Jungle rather than copying data. The migration checklist (documented in
`docs/design-decisions.md`'s sources) suggested "consider gated or public filtered directory" —
also not decided.

**Constraints on whichever option is chosen**, both sourced:
- **Opt-in only.** A member's own consent controls what appears (per the "Directory & consent"
  dashboard screen above and `apps/site/content/members.md`'s "opt-in fields only" note).
- **Member Jungle stays the data source of truth** regardless of display mechanism (C5) — an
  embed reads live; it does not sync a copy into Wix.

`[[decision needed: embed vs link-out, and public vs member-gated visibility — flag to Sunil/Bhanu
before building this screen]]`

## Build gate

**Nothing in this spec is buildable until the retain/integrate/replace assessment is approved.**
`PROJECT-RULES.md` is explicit: membership runs on Member Jungle as provisional system of record, do not
rebuild it on Wix before that assessment, link out and do not duplicate, and never hold the member
or payment register in two places.

Read against that, the screens below are a design study, not a build order. Wix Members Area login,
a Wix member-role store, and dashboard screens carrying membership status, renewal date, invoices
and corporate seats are the Wix-side member system the rule names. Even read-only display needs the
data to arrive somewhere, and this spec says at its own open items that the Member Jungle
integration mechanism is unknown, so it specifies the surface before the thing that decides whether
the surface may exist.

Until the assessment lands, the portal is **link-out only**: a gated shell that sends members to
Member Jungle for membership, billing, directory and registration. That shell is buildable now, on
staging, because it holds no member data: it is navigation and copy. What is not buildable is any
screen that displays or writes membership status, renewal dates, invoices, directory consent or
corporate seats. If retain-and-integrate is later
chosen, Member Jungle stays authoritative and Wix may be a defined read-through presentation
surface with no copied register.

A privacy assessment gates migration, integration and any processing of live personal data. It
does not gate a static prototype that holds none. Before either of those steps: `membership-crm.md:24-26` requires a
PIA before migration plus a cross-border assessment, and `inzbc-ai-operating-system.md:662-673`
requires one before connecting Wix and Member Jungle. An approved PIA, data map, retention policy
and access/correction process are all prerequisites.

## Dependencies
- Foundation decision on Member Jungle (retain/integrate/replace) — formally still `PROPOSED`.
- Approved PIA, data map, retention policy, access and correction process, cross-border assessment.
- `docs/forms-spec.md` (#160) and `docs/design-decisions.md` (#155) are referenced here. #160 cites
  this file back, so neither can depend on the other having landed. Both references are to content,
  not to merge state, and neither blocks this document.
- Bhanu's access-control model, and the system-1-vs-system-2 conflict flagged above.
- The website shell (Paras) — this portal sits behind Wix Members Area gating on top of it.
- Final fee/tier structure from INZBC before the Billing screen can show real numbers.

## Open items
1. SSO vs. separate Member Jungle login (`member-portal.md`'s own open item) — unresolved.
2. Whether "Member portal access control... on the auth/RBAC model" (bhanu.md) means the internal
   GitHub-OAuth system or just naming parity on Wix's own roles — needs Bhanu's clarification.
3. No Member Jungle API/integration mechanism is documented anywhere — confirm what actually
   exists before designing live-data screens vs. static link-outs.
4. Member Directory: embed vs. link-out, and public vs. member-gated (OI-7) — undecided.
5. Exact fee/tier structure (D9) — `OPEN`, blocks the Billing screen's real content.
