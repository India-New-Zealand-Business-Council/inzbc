# What INZBC can test, week of 4 August 2026

One slice, deployed and reachable, that Sunil can use without us driving it. Everything else stays
in the repo until it is honestly demonstrable.

## The slice: the FTA Opportunity Explainer

Chosen because it is the only thing that is finished rather than nearly finished. It is merged,
tested, packaged, and its container is built and smoke-tested on every pull request by the `docker`
CI job, which already asserts `/health`, a matched query, a no-match escalation and that the UI is
served same-origin. Nothing needs writing to demo it. It only needs deploying.

It is also the right thing to show first. It answers a real member question, it draws only from a
sourced corpus, and it makes **no model call at all**, so it cannot invent a trade fact. That is the
governance story this project is meant to prove, in a form a non-technical person can check in a
minute.

**What Sunil can do:** open a URL, ask "dairy", "wine", "manuka honey", and read a sourced answer
with its citation and verified-at date. Ask something outside the corpus and watch it escalate to
INZBC rather than guess.

**What he should try, because it is the point:** ask about milk, cheese or butter. The answer says
those are *excluded* from India's tariff concessions. A system that only told the good news would be
useless to an exporter.

## Verified working, 4 August 2026

Run locally against the merged `main`, not asserted. The API was started, queried and stopped.

    GET /health
    {"status":"ok"}

    GET /api/fta/query?q=wool
    status: matched
      Wool | MFAT National Interest Analysis | confidence: High

    GET /api/fta/query?q=dairy%20tariff
    status: matched
      Dairy - milk, cheese, butter                          | High
      Dairy - bulk infant formula and other dairy preparations | High

    GET /api/fta/query?q=how%20do%20I%20export%20software%20to%20India
    status: no_match
    answers: []
    action_required:
      "INZBC does not hold a verified answer to this question in its FTA source
       corpus. Rather than provide an unverified answer, this query is referred
       to INZBC."
      next_step, escalation_path, status_line, jurisdiction,
      approved disclaimer, confidence: Action Required

The third response is the one to show INZBC, and it is the point of the whole build. Asked
something outside the sourced corpus, the system does not guess, does not soften, and does not
produce a plausible answer with a hedge. It returns no answers at all, says so plainly, and hands
the question back with a route to a human.

The `answers` array is empty rather than absent, and the escalation carries no evidence fields, so
there is no shape of response in which a no-match could be rendered as a finding.

The second response also demonstrates ranked retrieval (#54): multiple matches ordered by weighted
keyword relevance, each with its own citation and confidence, rather than an unordered set.

## Deployment

ADR-0004's 27 July amendment governs: zero recurring cost, no payment method on any account. Cloud
Run stays deferred until Phase 2 stores member data and the NZ Privacy Act residency requirement
returns. Tracked as #99, which was gated on billing confirmation (#93) that the amendment made moot.

**Deploy the combined image on Render, not the Render-plus-Cloudflare split.** ADR-0004 names that
split as the target and it does not work today without new code: `apps/fta/ui/src/api/client.ts`
defaults `baseUrl` to the empty string and nothing passes one, so a Cloudflare-hosted UI would
request Cloudflare's own `/api/fta/query`, and `services/api` installs no CORS for the cross-origin
case. The Dockerfile already serves API and UI from one origin, and the `docker` CI job smoke-tests
exactly that arrangement. Splitting the hosts is separate work: a configurable API origin, a CORS
policy, and Cloudflare build configuration.

**The honest caveat, and it needs saying before the session, not during it.** Render's free tier
sleeps after roughly 15 minutes, with a cold start near a minute. ADR-0004 already records this as
adequate for a warmed demo and poor for an unattended acceptance session. So: warm it immediately
before any client session, and do not use the free tier for the formal acceptance session in #133.

## What is deliberately not in this demo

Saying so plainly is more useful than a longer list of what is.

- **SIP daily run.** The pipeline, orchestrator, scoring and source register are built and tested,
  but there are no API endpoints and no database behind them yet. ADR-0005 was accepted on 30 July
  and the schema landed on 31 July; the endpoints (#120, #121, #125) are the next work.
- **SIP review and approval UI.** PR #166 is a fixture prototype. Its mandatory-source gate checks
  eight source codes that do not exist in the 112-source SIP-185 register, and selected candidates
  do not reach the generated brief. Demoing it would show a workflow that does not yet do what it
  appears to do.
- **Comms Assistant.** PR #162's UI is real, but `/api/comms/draft` does not exist and the redaction
  layer ahead of every external model call is still unowned (#37, #53). Nothing should reach a model
  from that surface until it does.
- **Member portal.** Blocked on the Member Jungle retain/integrate/replace assessment (#95) and a
  privacy assessment (#113). Not a build task yet.
- **The rebuilt website.** Being built on the `INZBC Staging` duplicate. The redirect map exists;
  the page tree does not.

## What INZBC owes before the next slice

These are not technical blockers, and none can be resolved by us:

1. **Member Jungle decision** (#95). Blocks the member portal entirely.
2. **Named human reviewer for AI-drafted output** (#96). A governance requirement, not a preference:
   nothing AI-drafted publishes without one.
3. **The separation-of-duties exception.** `launch-config.md` assigns Sunil both Primary Analyst and
   CEO / SIP Owner, while the contract says nobody approves their own output. ADR-0005 allows a
   recorded exception naming the approver, reason and review date. Sunil has to approve that before
   the controlled launch runs.
4. **The two disputed figures.** Two-way trade $3.68b (guide) versus NZ$3.95bn (MFAT, year ended
   December 2025), and member count 160+ versus 200+. Neither goes on a page until confirmed.
5. **Collection-engine secrets** in the org repo. Blocks running the collector end to end.

## Order of work this week

1. Deploy the FTA slice (#99). Everything below is behind it in value because nothing else is
   demonstrable yet.
2. Run endpoints and decision endpoints against the new schema (#120, #125), now that
   `schemas/api-contract.md` reflects ADR-0005.
3. Find an owner for the redaction layer (#37). It blocks #53 and #65 completely, and it is the one
   security control with nobody's name on it.
4. Build the staging page tree from the redirect map, so there is something for INZBC to react to.
