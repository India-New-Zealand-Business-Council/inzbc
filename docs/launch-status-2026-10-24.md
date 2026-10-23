# Launch status, 24 October 2026

**Recorded by:** Bhanu Gupta, tech lead, 24 Oct 2026 (Pacific/Auckland).

This replaces the "blocked on INZBC" lines that the plan, handoff and handover pack carried until
today. It records what the tech lead reported; the client's own written record should be linked
here when it is filed.

| Item | Status as of 24 Oct |
|---|---|
| Public website | Live. `inzbc.org` serves the `inzview` build on INZBC's main domain. Changes still go live only when someone publishes in Vibe; pushing to `main` does not publish |
| #189 production launch approval | Cleared. The tech lead reports INZBC has given the go-ahead for production use |
| #55 first production SIP run | Unblocked. The tech lead reports the SIP-191 authorisation and the PAT for live collection are in place |
| Other modules | To go live as each is completed, on the same approval |

## What does not change

- The coordinator agent still cannot run production or distribute. `production_enabled` is sealed
  to `False` in `apps/sip/core/agent_loop.py`; it rehearses a run on a copy and stops at QA. A
  production run is made by people through the platform, through the same human gates.
- Distribution still opens only on a recorded distribution authority naming its recipient.
- The decision-signing settings are a deployment step: set `SIP_DECISION_SIGNING_KEY` server-side,
  then turn on `SIP_REQUIRE_SIGNED_DECISIONS` once runs recorded before #448 are closed
  ([secrets register](secrets-register.md#decision-signing-key-rollout-and-rotation-prerequisites)).

## Still to record

- Link INZBC's written approval for #189 and the SIP-191 authorisation for #55, then close both
  issues against those records.
- Record the first production run's run number and outcome here once it has happened.
- Open decisions (assistant, FTA Explainer on the site, platform hosting, signing enforcement)
  are in [decisions-needed.md](decisions-needed.md).
