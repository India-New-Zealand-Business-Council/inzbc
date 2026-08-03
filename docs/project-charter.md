# Project Charter — INZBC AI Operating System

Version 1.0, issued 3 August 2026. **Status: proposed, awaiting sponsor and supervisor
signature.** Nothing here is client authority until it is signed. Read it as the shape the team
is proposing, not as scope INZBC has agreed.

The signed copy is submitted on the Studio 5 charter form (IA728001, Block 3 2026). This is the
same content, kept in the repository so it can be reviewed, diffed and updated alongside the work
it describes. Where the two differ, the signed form is the record; a change here that matters to
the client is carried into a new signed version rather than only landing in git.

Contact details for learners, the sponsor and the supervisors are deliberately **not** recorded
here. They live on the submitted form only.

Two client documents are cited below and are not in this repository: the module menu put to INZBC
for prioritisation (fifteen modules, four selected), and the INZBC Digital System Overview supplied
3 August 2026, which is where the ten FTA sectors and the nine-part system come from. Both are held
by the client. Anything drawn from them is attributed rather than asserted, because a reader cannot
check them here.

---

## 1. Identification

| Field | Detail |
|---|---|
| Programme | INZBC AI Operating System (AIOS) |
| Client | India New Zealand Business Council, inzbc.org |
| Executive Sponsor | Sunil Kaushal — scope, content, budget, go-live. Sole Wix account owner, so only he can duplicate the site, and only he authorises cutover. Whether other collaborators still hold publish rights on the live site is **unverified** (`website-redirect-map.md`), so this is an authority statement, not a technical barrier |
| Delivery team | Bhanu Gupta (technical lead, platform), Roshan (intelligence and data), Paras (product and user experience) |
| Supervisors | Dr Asanthika Imbulpitiya, Dr Sonia Gul |
| Academic context | Studio 5, IA728001, Block 3 2026 — 16-week placement |
| Duration | Week 1 commenced 13 July 2026 |
| Primary repository | `India-New-Zealand-Business-Council/inzbc` — shared API, database schema, SIP, FTA, Comms, site |
| Second repository | `India-New-Zealand-Business-Council/daily-india-nz-news-agent` — the SIP collection engine |

---

## 2. Summary

INZBC represents the New Zealand–India trade relationship to ministers, diplomats, exporters and
its own members. Its digital systems have not kept pace with that remit: the website hands
membership applications to a separate platform, content ownership is unclear, and organisational
knowledge is spread across personal drives and accounts.

This project builds a connected digital operating system for the Council, not a website. It spans
nine modules over two repositories sharing one database, one API contract and one governance
spine.

Four modules are the committed build of this engagement, selected by the client from a
fifteen-module menu: the FTA Opportunity Explainer, the Trade Intelligence Digest produced by SIP,
the AI Communications Assistant, and the public website rebuild. The remaining five are specified,
sequenced behind phase gates, and handed over.

The engineering problem throughout is trust. Every output reaching a member or a minister must be
traceable to an approved source and to a named human who authorised it, and no path may exist that
bypasses either. That constraint, rather than the feature list, is what makes the work difficult.

---

## 3. Objectives

| # | Objective | How it is judged |
|---|---|---|
| O1 | SIP: a governed intelligence platform that collects, verifies, scores, routes, reviews, approves and audits daily India–NZ trade intelligence | No distribution path bypasses human approval; separation of duties enforced; the decision record is append-only |
| O2 | An FTA Implementation Centre and Opportunity Explainer answering sector questions from sourced material and never from invention | Every answer cites its source with an effective date; a question with no match returns a distinct no-match result carrying no evidence fields |
| O3 | An AI Communications Assistant for staff drafting, adversarially tested before any staff use | A documented security review with findings closed; no external model call can leave the process unredacted |
| O4 | A rebuilt public website on a duplicate of the live site | Redirect map covering every live URL, verified after cutover; sitemap resubmitted; 404s monitored for the agreed observation window; WCAG 2.2 AA |
| O5 | The cross-cutting spine every module depends on | Each of identity and roles, system-of-record map, security, privacy, AI governance and accessibility exists as an approved artefact rather than an intention |
| O6 | A system INZBC can operate without the team | Operator documentation, secrets register with named owners, tested restore, recorded handover |
| O7 | The remaining programme specified rather than informally understood | Module specifications, a decision register with owners and consequences, and phase gates a later team can pick up |

---

## 4. The nine modules

Complexity and ownership are the team's own assessment, recorded in
[`docs/modules/README.md`](./modules/README.md) before build began.

| # | Module | Complexity | Lead |
|---|---|---|---|
| 1 | Public website — home, about, board, events, news, sponsors, FTA overview, join pathway | Medium — Wix CMS, dynamic pages, forms, SEO, WCAG 2.2 AA | Paras |
| 2 | Member portal — gated resources, renewals, briefings, request forms | High — identity, roles, links to Member Jungle | Paras |
| 3 | Membership and CRM — records, categories, renewals, corporate seats, consent | High — system-of-record decision, payments, GST, migration | Bhanu with INZBC |
| 4 | Sponsors and trade services — pipeline, benefit delivery, introductions, delegations | Medium-High — evidence of delivery, confidentiality | Bhanu |
| 5 | Events and delegations — lifecycle, registration, VIP, check-in, follow-up | Medium — platform choice, registration, comms | Paras |
| 6 | FTA Implementation Centre — sourced knowledge base and the Opportunity Explainer | High — source governance, citations, effective dates | Roshan |
| 7 | SIP — collect, verify, score, route, review, approve, audit | Very high — RBAC, state machine, audit, fail-closed, human approval, separation of duties | Bhanu core, Roshan pipeline, Paras interface |
| 8 | AI Communications Assistant — staff-only drafting | Medium-High — controlled prompts, prohibited-data rules, human approval | Roshan and Paras |
| 9 | Executive and board dashboards — control state, actions, QA, distribution, metrics | Medium — reporting over the shared database | Paras |

### The collection engine, in its own repository

The SIP collection engine is a separate Python service in `daily-india-nz-news-agent`. It is
deliberately separate: it collects from untrusted external sources, so it is kept out of the
request-serving application and constrained to draft output only. It does **not** currently run on
a timer and does not send anything automatically; it prepares a draft. **It cannot distribute and
it cannot approve.**

### Cross-cutting spine

Not features. They apply to every module, and a module that ignores one is not complete.

| Concern | What it requires |
|---|---|
| Identity and roles | Member category vs entitlement vs portal access vs administrative authority, kept distinct |
| System-of-record map | One authoritative store per data type |
| Security | MFA, least privilege, separated environments, no secrets in source, managed secret storage and rotation, dependency scanning, protected branches, logging, alerting, quarterly access review, tested restore |
| Privacy | Assessment before member data or AI use, collection notices, minimisation, retention and deletion, access and correction, breach process |
| AI governance | Approved workspaces, prohibited inputs, redaction before any external call, human approval, no auto-publish |
| Accessibility | WCAG 2.2 AA on every public surface, built in rather than audited at the end |
| Separation of duties | Analyst captures. Reviewer checks. Approver releases. Administrator configures but cannot approve their own output |

---

## 5. Business requirements

Priority uses MoSCoW.

| ID | Requirement | Rationale | Priority |
|---|---|---|---|
| BR1 | Every AI-drafted output is reviewed and approved by a named human before publication or distribution, and that approval is recorded permanently | INZBC speaks to ministers, diplomats and exporters. One unreviewed false claim costs more credibility than the system saves in effort. An approval record that can be edited afterwards is not a record | Must |
| BR2 | No statistic, member count, board name or FTA detail is **invented**. Sourced material only, each traceable to its source. Where a fact is owed by INZBC, staging may show a visible `[[placeholder]]`; on a public page the item is omitted instead, because a placeholder shipped to a member is a defect | A plausible invented figure is more dangerous than a blank, because nobody checks it. This already caught a homepage figure that would have published 95% of NZ's exports rather than 95% of its exports *to India* | Must |
| BR3 | Member and personal data handled under the Privacy Act 2020, with a PIA before member data or AI use, collection notices, retention and deletion rules, and a breach process | Legal obligation, and the Council holds member data it did not collect for this purpose | Must |
| BR4 | Anything sent to an external model is redacted against an approved policy first, and the call is refused outright when no policy exists | Absence of a policy must mean refusal, not permission. A redaction layer satisfiable by a rule set matching nothing gives false assurance, which is worse than no redaction | Must |
| BR5 | The FTA Explainer answers only from the sourced corpus, cites each source with its effective date, and returns a distinct no-match result when it has no answer | Tariffs reduce in stages, so the same product has a different correct answer in different years. A no-match sharing the shape of a match will eventually be rendered as one | Must |
| BR6 | The website is rebuilt on a duplicate. The live site is not edited, and the domain is switched once, on the account owner's written authority | Only the account owner can publish. Wix content-manager writes hit live data instantly with no draft step, and there is no complete external backup of a Wix site | Must |
| BR7 | Every live URL is mapped to its destination before cutover | Inbound links and search rankings are an asset accumulated over years and not quickly rebuilt | Must |
| BR8 | Separation of duties enforced in SIP: analyst captures and assesses, reviewer checks sources and classification, approver authorises release, administrator configures but cannot approve their own output | A control one person can execute end to end is not a control. This is what makes the audit trail meaningful rather than decorative | Must |
| BR9 | One system of record per data type. Member and payment registers never in two places; Member Jungle is the provisional membership system of record | Two registers diverge, and reconciling them costs more than either system saved | Must |
| BR10 | Every public surface meets WCAG 2.2 AA, including the 320px reflow case and contrast on the brand palette | Built in costs less than audited at the end, and the audit already found contrast failures in the existing palette | Should |
| BR11 | INZBC holds organisational ownership of every account, domain, social account and credential, with secrets registered by name, owner and scope on a 90-day rotation | No important system should be controlled through a personal email or phone. The Council must still hold the system after the placement ends | Should |
| BR12 | A competent operator with no prior involvement can run the system from the documentation alone, with a tested backup and restore | The team leaves after 16 weeks. Documentation written for the people who built it is not a handover | Should |

---

## 6. Scope

### In scope

**Committed build — the four modules the client selected**

- FTA Opportunity Explainer, with the tariff database and three levels of information depth.
  Sector coverage is **not settled**. The Digital System Overview lists ten (wool, wine, seafood,
  primary industries, tourism, education, defence and security, investment, immigration, sports);
  `client-answers.md` D19 proposes a different order and set; `requirements.md` and
  `fta-source-corpus.md` both still record it as awaiting INZBC. One list has to win before build,
  and closing it updates those documents in the same change.
- Trade Intelligence Digest produced by SIP: collection, source register, scoring, review, QA,
  approval, distribution and audit.
- AI Communications Assistant for staff drafting, adversarially tested before use.
- Public website rebuild on the duplicate, with the redirect map and accessibility.

**Specified and gated** — modules 2, 3, 4, 5 and 9, built as the gates allow.

**Cross-cutting** — the spine in section 4, plus the governance document set: decision register,
RACI, account and licence register, threat model, incident response, data inventory and retention,
migration and rollback, test plans, operational runbooks.

### Out of scope

- WIA, Kiwi Indians, WAIP, and any political or personal digital systems. These stay outside the
  INZBC environment for governance, privacy and ownership reasons.
- AI Readiness Reports, the Innovation and Commercialisation Network, and the Hindi-language
  toggle. Offered in the module menu and not selected.
- Rebuilding membership on Wix before the retain / integrate / replace assessment closes.
- Editing or publishing the live `inzbc.org` site.
- Procuring or committing to licences and hosting.
- Phase 4 automation and reporting in full — specified with gates and handed over, not built.
- Migrating historical member or financial data before the system-of-record decision is made.

---

## 7. Delivery phases and gates

A gate is not a status update. It is signed evidence, and the next phase does not start without it.

| Phase | Gate | State at issue |
|---|---|---|
| Phase 0 — SIP controlled launch, 27–31 July 2026 | All five runs recorded, source outcomes recorded, exceptions resolved or carried, QA completed daily, no unauthorised external publication, final launch review approved | **Not evidenced as run.** The window has passed, but the launch pack is still at v0.9 review draft, the only approved controlling document is SIP-050, and the repository holds a blank run-record template rather than five completed records |
| Phase 1 — Assessment and foundation | Signed by Executive Sponsor, Finance Owner, Privacy Owner and Technical Lead | Partly complete, gate **not signed**. The architecture, contracts and content inventory exist; the governance, privacy, security, data, membership, testing and operations document sets do not yet |
| Phase 2 — Core systems | Privacy, security, accessibility, data, UAT and recovery tests passed | Build work under way **ahead of the Phase 1 gate**, see the note below |
| Phase 3 — Activation | Content governance, AI evaluation and business-owner acceptance passed | Not started |
| Phase 4 — Automation and reporting | Automation controls, failure handling, support and audit tests passed | Not started |

**Phase 2 work is running ahead of its gate, and that is a deviation, not an oversight.** The brief
says Phase 2 starts only after the Phase 1 gate is signed. Two of the four signatories have not
been named by INZBC, so the gate cannot be signed by anyone, and a placement that stopped until it
was would deliver nothing. The team is therefore building against the specifications while the
gate stays open, and nothing is deployed, published or given real data until it closes. INZBC
should know this is happening rather than discover it at handover.

The engagement does not reach the end of Phase 4. Note also that the brief places two of the four
priority modules, the FTA Centre and Explainer and the AI Communications Assistant, in Phase 3, and
says Phases 3 and 4 need a separate approved business case. Delivering all four therefore requires
either that approval or an agreed variation to the phase boundaries. This is a scope conflict for
the sponsor to resolve, not one the team can resolve by working harder. Detail in
[the programme brief](./inzbc-ai-operating-system.md) §9.

### The four foundation decisions

Core build past Phase 1 is gated on four decisions only INZBC can make.

| # | Decision | What it gates |
|---|---|---|
| F1 | Membership platform: retain Member Jungle, integrate, or replace. Team recommendation: retain and integrate for now | Modules 2 and 3 |
| F2 | Internal platform: Microsoft 365 with Power Platform, or a repository-hosted application | Internal operating environment, document repository, dashboards |
| F3 | Identity model: which service controls public members, staff, board members, administrators and service accounts | Every login-gated surface, and the separation of duties SIP depends on |
| F4 | Budget and ownership: approved scope, licence and hosting budget, support model, named INZBC owners | All provisioning and deployment, and the support model after handover |

---

## 8. Roles

| Member | Lane | Responsible for |
|---|---|---|
| Bhanu Gupta | Technical lead — foundation, security, integration | Shared contracts (API, schema, state machine), SIP core, identity and role model, security and privacy controls, deployment, code review and merge, architecture decisions, handover pack. Sole merger to `main` |
| Roshan | Intelligence, sources, data, FTA | Source register and collection engine, scoring and evaluation, FTA corpus, tariff data and sector structure, integration tests. Writes through the shared API |
| Paras | Public site, member experience, UI | Website rebuild and content, member portal and event surfaces, SIP review and approval interfaces, dashboards, WCAG 2.2 AA. Reads through the shared API |
| Sunil Kaushal | Executive Sponsor | Scope and priority, content and factual approval, the four foundation decisions, Wix account ownership, written go-live authorisation |

The lanes exist so two people do not edit the same thing at once, not to fence anyone out. Shared
contracts change through the technical lead, because a contract that shifts underneath a dependent
lane costs more than the change saved.

The division is **not permanent**. This is a 16-week placement and INZBC holds the system
afterwards. Every role is documented so it can be performed by the sponsor, a future contractor, or
a different team member: the handover pack targets a competent operator with no prior context.

---

## 9. Technical complexity, and why it is there

Each item exists because a simpler version was tried, specified or reviewed and found unsafe.

| Problem | Why the obvious approach fails | What was built, and where it is |
|---|---|---|
| Recording who approved what | A mutable approvals row can be overwritten, leaving no trace of what it previously said. An audit trail that can be edited is not an audit trail | Three append-only decision streams — CEO Ruling, Report Approval, Distribution Authority — with database-level append-only triggers, nine tables and a current-decisions view ([ADR-0005](./decisions/0005-decision-approval-distribution.md)). The DDL is on `main` and CI applies it against PostgreSQL; it is not yet migrated to a running database and no endpoints expose it |
| Two people deciding at once | Row locking serialises writers but does not detect conflict: the second re-reads the head the first just wrote and commits over it. Both land, and the loser is never told | Compare-and-swap concurrency where the caller passes back the revision it read; a stale decision is refused with the reason. The schema and its constraints are on `main`; the repository that enforces the check is in flight against #125 |
| Sending member data to an external model | Redaction as a convention is not redaction. A rule set matching nothing satisfies an "is it configured" check, and a backreference in a replacement re-emits the original value while counting a successful redaction | A gate that refuses without a policy, rejects backreference replacements and empty-matching patterns at load, bounds payload size, and redacts the union of overlapping spans. In review on #180, not yet on `main` |
| Preventing an unsupported claim reaching a member | A confidence threshold still renders an answer. A no-match sharing the shape of a match will eventually be rendered as one | A distinct no-match type carrying no evidence fields, enforced across four independent layers: domain type, wire envelope, generated types, interface component |
| Guaranteeing coverage of mandatory sources | Keying the coverage gate on source name under-counts silently, because two names are duplicated across the NZ and India lists | The gate re-keyed on stable source identifiers, with 112 mandatory sources verified against the approved register |
| Stopping an illegal state change | A permissive default fails open: an unrecognised transition is allowed because nothing refused it. Reporting a lost race as an illegal move sends the operator to the wrong diagnosis | A fail-closed state machine with legal transitions only, hard human gates, a terminal stopped state, an append-only transition history, and staleness checked before legality. The gates and that history live in the in-memory orchestrator; the durable adapter deliberately does not re-implement them, so a caller writing straight through it can still commit a legal but human-gated move. Closing that is #119, server-side separation of duties |
| Untrusted text reaching a model | Article text is attacker-controlled. A scorer that trusts model output to match its contract will accept anything the model returns | Prompt-injection and contract-regression suites treating source text as untrusted, with strictly validated scoring that rejects non-conforming output rather than coercing it |

---

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Cutover damages the live site or loses search rankings | High | Build on a duplicate; complete redirect map; record Site History version and export collections before cutover; written sign-off |
| An AI output publishes something false in the Council's name | High | Sourced material only; named human reviewer; no distribution path that bypasses approval; append-only approval records; separation of duties |
| Personal or member data reaches an external model | High | Redaction gate that refuses without a policy; adversarially reviewed; payload bounded; prohibited inputs defined |
| Foundation decisions stay open and Phase 2 cannot be gated | High | Decision register with owners; raised at each weekly meeting; modules specified so blocked work does not block everything |
| Nine-module programme against a 16-week placement | Medium | Phase gates; four priority modules committed; the remainder specified and handed over rather than half-built |
| Key knowledge sits with one contributor | Medium | Decisions recorded as ADRs; module specs written before build; handover pack written for an operator with no context |
| Systems remain tied to personal accounts at handover | Medium | Account and licence register; organisational ownership of domains, social accounts and logins before sign-off |
| Collection engine breaks silently against changed external sources | Medium | Source outcome recording, exception register, alerting on failed jobs, daily QA during controlled operation |

---

## 11. Resources

**Hours.** The Studio 5 weekly timesheets are the record. Weeks 2 and 3 came to 40 and 38.5 hours
for the technical lead, logged per day against the commit and review record. That is the observed
rate rather than a commitment, and the other two lanes keep their own timesheets. Weeks 12 and 13
are held as float, because every prior estimate on this project that assumed no slippage has
slipped.

**In place.** GitHub organisation with two repositories, project board and CI; local development
environments; PostgreSQL; the Wix account with a duplicate site; Member Jungle (client-held); a
model API key for development.

**Required from INZBC.** Organisation-level model credentials so the deployed system does not run
on a personal key; a hosting budget and billing owner; brand assets and approved organisation
facts; FTA and membership source material; named Privacy and Finance owners to sign the Phase 1
gate.

---

## 12. Ways of working

- Backlog-driven across two repositories and one project board. Each engineer keeps a worklog and
  normally takes the top open item; taking a lower one is fine when client priorities move,
  provided the reason is written down.
- Every change reaches `main` through a reviewed pull request naming the issue it delivers. No
  direct pushes. `CODEOWNERS` records which paths belong to the technical lead, but it is documentation
  only until code-owner review protection is enabled, which needs repository admin and a paid plan.
  The routing is a convention the team keeps, not a control the platform enforces.
- Reviews correct the content in dispute rather than annotating it. A specification carrying a note
  that says it is wrong is still wrong for the next person who reads it.
- Linting, type checking, tests, coverage, secret scanning, link checking and workflow linting run
  on every pull request and block the merge. Static analysis runs report-only until its baseline is
  confirmed clean, and dependency updates come from Dependabot rather than a blocking audit job.
  Both are tracked as work to tighten, and neither is claimed as enforcement today.
- Security-touching changes get an adversarial review, and findings are reproduced by execution
  before they are accepted or dismissed.
- Decisions that shape the system are recorded as ADRs with consequences and rejected alternatives.
- Every Wix editor session is logged with before and after text, because Wix records *that*
  something changed but not what it said.

### Change control

Scope changes are agreed with the sponsor and recorded before work starts, not reconciled
afterwards. A change that adds a module must name what it displaces: with three part-time
contributors and a fixed end date, adding work without removing work is a decision to deliver
something else late. Phase gates are not waived; if evidence is missing the gate fails and the
reason is recorded.

---

## 13. Success criteria

The engagement is successful if all of the following are true at handover:

- The four priority modules are delivered and demonstrated on a deployment INZBC can exercise
  without the team present.
- SIP runs as a structured application rather than a manual workbook, with separation of duties
  enforced and a complete audit trail.
- No published output originated from an AI system without a named human approving it, and that
  approval record cannot have been edited.
- Cutover completed on the client's written authority, with every mapped URL verified to resolve
  and 404s monitored across the agreed window afterwards. Search rank cannot be guaranteed at the
  cutover instant, so it is not claimed as an acceptance condition.
- INZBC holds organisational ownership of every account, domain and credential the system depends
  on, with a tested restore.
- A competent operator with no prior involvement can run the system from the documentation alone.
- The remaining five modules and Phase 4 are specified with their gates, so the next stage starts
  from a position rather than from scratch.

---

## Related

- [Programme brief](./inzbc-ai-operating-system.md) — architecture, phases, INZBC inputs, controls
- [Module map](./modules/README.md) — the nine modules and their specifications
- [Discovery](./discovery.md) — site audit, information architecture, open items
- [Requirements](./requirements.md) — user stories, acceptance criteria, traceability
- [Decision records](./decisions/) — ADR-0001 to ADR-0005
