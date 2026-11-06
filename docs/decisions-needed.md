# Decisions needed

**Opened by:** Bhanu Gupta, tech lead, 24 Oct 2026. Each item is left open for discussion. Nothing
here is being built until it is decided. Record the outcome, date and who decided in the
item, then move it to the bottom.

## SIP operational decisions — Sunil / INZBC (requested 6 Nov 2026)

The following four questions belong to **Sunil Kaushal as CEO / SIP Owner and INZBC
account/operational authority**. Bhanu is responsible for technical design, review, and
implementation once the relevant client decision is documented. This section is a
**request for decisions, not evidence that Sunil has approved anything**.

**Separate deployment scopes:** [#99](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/99) is the previously scoped public FTA-only demo: Render API plus same-origin FTA UI, **without Postgres, member data or SIP operations**. Its issue discussion records earlier tech-lead approval for deployment preparation and an INZBC-owned account, but no created Render service or verified live endpoint. The pending decision below applies to the **full staff/SIP platform** (authenticated API, Postgres, operations and backups). It does not itself revoke the prior FTA preparation approval or authorise a new public go-live. If INZBC intends to supersede the FTA scope, record the explicit dated decision separately.

See
[SIP walkthrough](sip/SUNIL_SIP_WALKTHROUGH_2026-10-27.md),
[first-run plan](sip/LIVE_E2E_PROOF_PLAN_2026-10-27.md) and
[post-handover blockers](operations/post-handover-open-work-2026-11-04.md).

| Decision for Sunil | What needs an explicit answer | Status / evidence |
|---|---|---|
| **1. Staff/SIP platform hosting and operating account** (separate from the FTA-only scope of [#99](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/99)) | Confirm the INZBC-owned staff-platform account, provider/plan and cost, Postgres location, named operations/backup owner, and whether isolated staff/SIP staging may be provisioned. Preserve ADR-0004's zero-cost FTA baseline unless INZBC formally revises it. | **Pending Sunil's written staff/SIP decision** — date, environment, scope, approver and source link: `[[not yet supplied]]` |
| **2. First agent-to-API connection** ([#62](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/62), [#55](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/55)) | Authorise or decline connecting the Coordinator to a real authenticated, audited backend route for the first time; specify isolated staging/local versus production, allowed data and approved operator. A rehearsal is not a real run. This does **not** waive human QA, CEO, source, security, redaction, or separate distribution gates. | **Pending Sunil's written approval** — environment, boundaries, date and source link: `[[not yet supplied]]` |
| **3. Signed decisions and enforceability** ([#448](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/448)) | Decide INZBC's operational signing requirement, accountable key custodian, legacy unsigned-run policy, and conditions for enforcing `SIP_REQUIRE_SIGNED_DECISIONS`. Distinguish server-held signatures from the optional per-approver proof in ADR-0010. Bhanu tests and implements the approved staged rollout; no keys or signatures are to be supplied in GitHub text. | **Pending Sunil's written policy decision** — date, scope and source link: `[[not yet supplied]]` |
| **4. Who records source-verification evidence** ([#55](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/55)) | Resolve the draft's **Analyst** label versus the implementation's **Quality Reviewer / SIP Owner** permission. Name the recorder, who independently checks the evidence, and any formally approved separation-of-duties exception. Confirm the controlled SIP-184/SIP-185 procedure before changing role permissions or claiming independent QA. | **Pending Sunil's documented role decision** — people/roles, date and controlled-procedure reference: `[[not yet supplied]]` |

**Until Sunil's answers are recorded:** do not provision a staff/SIP platform service on the
strength of this table; do not wire the agent to a live route, require signatures in a deployed
environment, or change who may record verification evidence. The earlier FTA-only
demonstration scope remains separate and subject to its own documented deployment and
public-publication controls. Keep
`production_enabled=false`, and do not schedule collection, publish, distribute or
attribute a decision/signature to Sunil from an unconfirmed conversation.

**Delivery split (not additional approvals):** Bhanu can design and review the
missing run-state routes and the SIP-185-code planner prompt correction; the UI
owner can address seed-note incompatibility and Comms reviewer UI in an approved
lane. Technical fixes still need reproducible tests and the normal PR review.
A proposed 27 November demonstration may show an isolated, authorised path
through CEO decision, with agent wiring *designed but disabled* unless Sunil
separately approves its first connection. This target is not a new SIP-191
launch or distribution authority.

## 1. Platform assistant (chatbot)

**Where it stands.** Built and merged in #458: `POST /api/assistant/chat`, a read-only agent with
three tools (FTA corpus, recent run metadata, platform guide), and a chat box at the top of the
platform home screen. Tested against the live model and in the browser with a mocked API. **Not
usable by anyone**: the platform shell and its API are not deployed anywhere, and the server would
also need `OPENAI_API_KEY` and `REDACTION_POLICY_PATH`.

| Option | What it takes |
|---|---|
| A. Deploy it for staff | Package the platform shell, API and Postgres into one deployable service; someone creates it on the host and sets the secrets |
| B. A public chatbot on inzbc.org instead | A separate, narrower build (FTA and site questions only, no member data). INZBC decides scope and privacy, because members would type into it |
| C. Leave it in place, unused | Nothing. The box shows "not configured" wherever the platform runs without the settings |
| D. Remove it | One small PR removes the widget and the route |

**Owner:** tech lead; B also needs INZBC.

## 2. FTA Explainer on inzbc.org

**Where it stands.** inzbc.org has a placeholder at `/fta/explainer` ("Coming soon"). The
Explainer makes no model call and stores no personal data, and shows only confirmed corpus entries
with their citations, so it suits a public page.

| Option | What it takes |
|---|---|
| A. Build it into the website | Export the confirmed corpus into inzview and port the keyword ranking to the site. No hosting, instant, matches the site. Two copies of the ranking, kept honest by a parity test here |
| B. Embed the deployed app | Deploy the existing docker image (`render.yaml`) and embed it. One codebase, but a live service, CORS for the inzview origin, and a cold start of about a minute on the free plan |
| C. Keep the placeholder | Nothing |

Either way it goes live only on a Vibe publish. **Owner:** tech lead, with INZBC for public
wording; the app's heading and intro text still need a named reviewer.

## 3. Platform hosting

**Where it stands.** Only the database-free public FTA slice has a host configuration
([#99](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/99)); no live
Render endpoint has been verified. The staff-platform shell, its authenticated API and
Postgres have no deployed environment, so the staff platform (Trade Intelligence, Comms Assistant, Member Portal,
Executive Dashboard, onboarding) runs nowhere yet. The first production SIP run (#55) needs it.

**Decide:** which host and plan, who owns the account, and where the database lives.
**Decision authority:** Sunil / INZBC for hosting account, cost, operating responsibility and deployment go-ahead.
**Engineering owner:** Bhanu for architecture, implementation and verification after the recorded decision.

## 4. Signed-decision enforcement

**Where it stands.** Signed human decisions are built (#448) but off by default.

**Decide:** when to set `SIP_DECISION_SIGNING_KEY` in each deployed environment and when to turn
on `SIP_REQUIRE_SIGNED_DECISIONS`, after runs recorded before #448 are closed. Follow the
prerequisites in the [secrets register](secrets-register.md#decision-signing-key-rollout-and-rotation-prerequisites).
**Decision authority:** Sunil / INZBC for the signing policy, key custody and deployment go-ahead.
**Engineering owner:** Bhanu for staging checks, safe rollout and evidence after that approval.

## 5. Per-approver signatures

ADR-0010's next step, only if INZBC needs proof of authorship that does not rest on trusting the
server. **Owner:** INZBC.

## 6. Planner prompt: make a live run reach the QA gate

**Where it stands.** With a real model, no agent run reaches the QA gate
([baseline](research/agent-safety-baseline.md), section 6, #462). In the runs inspected, the planner
re-scored the same item until the step limit, and it cannot record the 112 SIP-185 outcomes
because the prompt does not give it the source codes. Both fail closed; neither is a safety fault.

| Option | What it takes |
|---|---|
| A. Change the planner prompt | Tell it which steps are done and give it the mandatory source codes, then re-run sections 1, 6 and the replay harness. This changes the system the research measures, so it is a plan change-log entry and a before/after comparison |
| B. Leave it | The agent stays a rehearsal that stops early; the research reports the limit as it does now |

**Owner:** tech lead (research design).

## 7. Independent attack suite

**Where it stands.** The 48 attacks and the section 6 scenarios were all written for this project,
which is the remaining "attacks are hand-written" threat to validity.

**Decide:** whether to adapt scenarios from an external suite (AgentDojo-style, ToolEmu-style) or
have someone outside the team write attacks blind to the controls, and who. **Owner:** tech lead.

## 8. Blind QA reviewer for the judge

**Where it stands.** The blind packet is ready
([agent-safety-human-qa-packet.md](research/agent-safety-human-qa-packet.md)); no reviewer has been
named. Judge vs an independent human stays "not measured" until one labels the 8 cases.

**Decide:** who reviews (not the rubric author), and by when. **Owner:** tech lead.

## 9. Reflection on the new results

Sections 6 and 7 of the baseline have no reflection in the plan's journal, the PDR worksheet or
the reflective report. These are assessed as Bhanu's own words, so they are his to write, not
drafted for him. **Owner:** Bhanu.

## 10. CEO ruling and run state (#127)

**Where it stands.** A CEO ruling or distribution authority is recorded as a decision, but
`runs.state` and `runs.version` are not moved with it, so the run can still read `Awaiting CEO
Decision` after a refresh. [ADR-0011 (proposed)](decisions/ADR-0011-ceo-run-state-consistency-proposal.md)
sets out the problem, why a simple "move to Continue" fix would block a later authorised
distribution, and a transactional design. Nothing is implemented.

**Decide:** the legal transition for each ruling (especially `Continue`, `Continue With
Correction` and a `Not Authorised` distribution), and whether to adopt the single-transaction
command. **Owner:** tech lead, with Sunil for any controlled-SOP change.

## Decided

None yet.
