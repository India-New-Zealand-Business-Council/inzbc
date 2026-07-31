# Workstreams — team development workflow

Three engineers, one monorepo. Each owns a worklog (their task backlog) and works in their own
lanes, so all three ship in parallel without collisions. Every change lands via a reviewed pull
request into `main`; Bhanu merges.

## Working from your worklog
Each engineer keeps a worklog at `docs/workstreams/<name>.md` — an ordered backlog, a done log,
current blockers, and a definition of done.

1. Fetch `main`. If your worklog's recorded base commit is behind `main`, rebase first.
2. Take the top item in **Next up**, or a lower one if client priorities have moved. Note why in
   the worklog when you skip.
3. Branch `feat/<name>/<slug>` off fresh `main`.
4. Build it to the quality standard below.
5. Open a PR with the evidence block, and move the item to **Done**.

## Quality standard (every change)
1. **Understand** — read the task and the code it touches; trace the real flow.
2. **Research** — confirm library/API specifics from docs; do not guess versions or props.
3. **Reuse before writing** — search (grep/LSP) for an existing helper, type, or pattern and use
   it. Do not reinvent a formatter, client, or validator the repo already has.
4. **Smallest diff** — change only what must change. No speculative abstraction, no dead flexibility.
5. **Root-cause bug-check** — fix the cause, not the symptom; check every caller of a changed function.
6. **Review** — self-review the diff; security-touching changes get an adversarial review.
7. **Checks pass** — lint, typecheck and tests all green before the PR. ("Done" = checks ran and passed.)
8. **PR** — open it with the evidence block. No AI attribution in commits or PRs.

## Lanes (how three work at once without colliding)
- Each engineer owns folders (see the per-engineer worklogs and `.github/CODEOWNERS`). Do not edit
  another engineer's lane without a `SHARED-OK:` note and their agreement.
- Shared contracts live in `/services/api`, `/database`, `/schemas` and are owned by Bhanu.
  Others build against them; contract changes go through Bhanu.
- Branches are short-lived, one per task, `feat/<name>/<slug>`, off fresh `main`. Rebase before PR.
- Never push directly to `main`. PRs only.

## PR evidence block (include in every PR)
```
## Evidence
- Task: <worklog item>
- Reused: <existing helpers/types reused, or "none — searched, none fit">
- Sources: <docs/URLs used, or "n/a">
- Checks: lint / typecheck / tests  (paste the command output)
- Review: self-reviewed; adversarial review if security-touching
- Watch closely: <the 1-2 things the reviewer should look hardest at>
```

## Repo layout (monorepo)
```
/apps/site        site (Velo) + content specs     (Paras)
/apps/sip         SIP control app                 (Bhanu core, Paras UI)
/apps/fta         FTA Explainer service + corpus  (Roshan)
/apps/comms       Communications Assistant        (Roshan/Paras)
/services/api     shared API, auth, audit         (Bhanu)
/database         schema + migrations             (Bhanu)
/schemas          shared types + API contract     (Bhanu)
/docs             planning + governance
/docs/workstreams this folder: per-engineer worklogs
```
The `daily-india-nz-news-agent` repo stays separate — the SIP collection engine. New repos only
when a component genuinely needs isolation; the monorepo is the default.
