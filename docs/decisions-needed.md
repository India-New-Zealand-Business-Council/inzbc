# Decisions needed

**Opened by:** Bhanu Gupta, tech lead, 24 Oct 2026. Each item is left open for discussion. Nothing
here is being built until it is decided. Record the outcome, date and who decided in the
item, then move it to the bottom.

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

**Where it stands.** Only the FTA slice has a host configuration. The platform shell, the API and
Postgres have none, so the staff platform (Trade Intelligence, Comms Assistant, Member Portal,
Executive Dashboard, onboarding) runs nowhere yet. The first production SIP run (#55) needs it.

**Decide:** which host and plan, who owns the account, and where the database lives. **Owner:**
tech lead with INZBC as account owner.

## 4. Signed-decision enforcement

**Where it stands.** Signed human decisions are built (#448) but off by default.

**Decide:** when to set `SIP_DECISION_SIGNING_KEY` in each deployed environment and when to turn
on `SIP_REQUIRE_SIGNED_DECISIONS`, after runs recorded before #448 are closed. Follow the
prerequisites in the [secrets register](secrets-register.md#decision-signing-key-rollout-and-rotation-prerequisites).
**Owner:** tech lead.

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
