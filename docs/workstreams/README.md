# Workstreams — how the team works with Claude Code

Three developers, one monorepo, zero collisions, top-tier output. Each person opens Claude Code,
says **"I'm <name>, continue my work"**, and the session picks up their backlog and ships a PR to
the quality bar below. Bhanu reviews and merges.

## The "continue" protocol
1. Dev opens Claude Code in the `inzbc` repo and says: **"I'm Paras, continue my work."**
2. Claude reads that dev's worklog: `docs/workstreams/<name>.md`.
3. It confirms the repo is current (`git fetch`; if the worklog's recorded SHA ≠ latest, it stops
   and asks the dev to reconcile — never continues on a stale base).
4. It takes the **top unchecked task**, creates a branch `feat/<name>/<slug>` off fresh `main`.
5. It builds to the **quality bar**, opens a **PR with the evidence block**, and appends a done
   line to the worklog.
6. Bhanu reviews the PR and merges.

Nothing else to memorise. The worklog is the backlog; the branch is the unit of work.

## The quality bar (the ladder — same order every time)
Encoded in the repo `CLAUDE.md`; the Stop gate + `verify` script enforce the last rungs.
1. **Understand** — read the task + the code it touches; trace the real flow.
2. **Research** — use context7 / web for any library or API; never guess versions or props.
3. **Reuse before writing** — grep/LSP for an existing helper, type, or pattern. Reuse it. Do
   not reinvent a formatter, client, or validator the repo already has.
4. **Smallest diff** — only the files that must change. No speculative abstraction, no dead flexibility.
5. **Self bug-check** — root-cause, not symptom; check every caller of a changed function.
6. **AI review** — run `/code-review` (or `/codex:adversarial-review` for security-touching code)
   and fix real findings before the PR.
7. **Lint / typecheck / test** — run the repo's own checks; they must pass. ("Done" = checks ran and passed.)
8. **PR** — open it with the evidence block. No AI attribution in commits or PRs.

## Collision rules (why three can work at once)
- **Lanes:** each dev owns folders (see per-dev files + `.github/CODEOWNERS`). Do not edit
  another dev's lane without a `SHARED-OK:` note and their nod.
- **Shared contracts** live in `/services/api` + `/database` + `/schemas` and are owned by Bhanu.
  Roshan and Paras build against them; contract changes go through Bhanu.
- **Branches:** short-lived, one per task, `feat/<name>/<slug>`, off fresh `main`. Rebase before PR.
- **Never** push directly to `main`. PRs only. Bhanu merges.

## PR evidence block (put this in every PR)
```
## Evidence
- Task: <worklog item>
- Reused: <existing helpers/types reused, or "none — searched, none fit">
- Sources: <docs/URLs used, or "n/a">
- Checks: lint ✓ typecheck ✓ tests ✓  (paste the command output)
- AI review: /code-review run, findings addressed
- Unsure about: <the 1-2 things the reviewer should look hardest at>
```
The "Unsure about" line is required — a PR claiming total confidence gets a harder look.

## Repo layout (monorepo)
```
/apps/site        Wix Velo + site content specs   (Paras)
/apps/sip         SIP control app                 (Bhanu core, Paras UI)
/apps/fta         FTA Explainer service + corpus  (Roshan)
/apps/comms       AI Comms Assistant              (Roshan/Paras)
/services/api     shared API, auth, audit         (Bhanu)
/database         schema + migrations             (Bhanu)
/schemas          shared types + API contract     (Bhanu)
/docs             planning + governance
/docs/workstreams this folder: per-dev worklogs
```
The `daily-india-nz-news-agent` repo stays separate — it is the SIP collection engine. No new
repos unless a component genuinely needs isolation; the monorepo is the default.

## Files
- `bhanu.md`, `roshan.md`, `paras.md` — each dev's lanes, backlog, and definition of done.
