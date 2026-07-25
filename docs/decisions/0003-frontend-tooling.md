# ADR-0003: Frontend tooling and testing stack

- Status: Accepted (adopt when the UI work begins)
- Date: 2026-07-24
- Deciders: Bhanu (tech lead), with Paras (UI owner) and Roshan

## Context
Paras's lane (`apps/*/ui`) is still backlog: the SIP review/approval UI, the design system, the
FTA Explorer embed and the Comms review UI have no code yet. Before that work starts we want the
tooling decided, so components are documented and tested from the first commit rather than
retrofitted. Two constraints shape the choice: the repo is **private** (so anything relying on
GitHub Advanced Security is a paid add-on, not free), and the platform runs on a near-zero cost
budget with a limited GitHub Actions minute allowance.

The industry-standard 2026 frontend stack is Storybook + Chromatic for component visual
regression, Vitest + React Testing Library for component unit tests, and Playwright for
full-page end-to-end tests. That split — component VRT on every PR, page E2E on the top flows —
is the widely adopted pattern.

## Decision
When UI work begins, `apps/*/ui` adopts:
1. **Storybook** — component workshop and living documentation; one story per component state.
   Backs Paras's token-driven design system (brand tokens swapped in when Sunil's kit lands).
2. **Vitest + React Testing Library** — component/unit tests (the 2026 default that replaced Jest).
3. **Playwright** — end-to-end tests for the highest-value flows first: the SIP QA → CEO-decision
   approval path and the FTA Explorer query → sourced-answer path. Runs entirely in GitHub
   Actions, no external service.
4. **Chromatic** — visual regression on Storybook stories, on every PR. Free tier is 5,000
   snapshots/month and works on private repos; the snapshot budget is watched, and VRT is scoped
   to design-system components rather than every story if the budget tightens.

Explicitly **not** adopted now: CodeQL/GitHub Advanced Security (paid for private repos —
Semgrep OSS covers SAST for free instead); semantic-release/changesets (no published package to
version yet).

## Consequences
Positive: components are documented and regression-tested from day one; the state-machine-driven
SIP UI gets real E2E coverage of its illegal-transition guards; and the stack is current industry
practice, so it is well documented and a future maintainer is likely to already know it.

Negative / mitigations:
- Four new tools is real setup cost. Mitigation: they land **incrementally with the first
  components**, not as empty scaffolding now — this ADR records the decision without adding dead
  config to the repo today.
- Chromatic and Actions minutes are finite on the free/private tiers. Mitigation: component VRT
  scoped to the design system; Playwright E2E scoped to top flows; both run on PRs, not on every
  push.
- Storybook/Playwright/Vitest live in Paras's lane; this ADR is agreed with him before any of it
  is wired.

## References
- Modern frontend testing (Vitest + Storybook + Playwright): https://www.defined.net/blog/modern-frontend-testing/
- Component testing in 2026: https://dualite.dev/blogs/component-tests-guide
- Chromatic pricing / free tier: https://toolradar.com/tools/chromatic/pricing
- CodeQL free tier (public only; private is GHAS add-on): https://agentdeals.dev/vendor/codeql
