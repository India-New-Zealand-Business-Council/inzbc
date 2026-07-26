---
name: quality-gate
description: >
  Run the INZBC repo's pre-PR quality gate and produce the PR evidence block. Use before
  opening or updating any pull request in this repo, or whenever the user asks to "run the
  checks", "run the quality gate", "check before PR", or "generate the evidence block". Mirrors
  every CI job (ruff, pytest+coverage, generated-type drift, frontend lint/typecheck/test/build,
  Storybook, secret scan) so failures are caught locally first.
---

# Quality gate

This repo's definition of "Done" is: lint, typecheck, and tests all pass, plus a PR evidence
block (see `docs/workstreams/README.md`). This skill runs those checks the same way CI does and
formats the result, so a PR is never opened red.

**Keep this file in step with `.github/workflows/ci.yml`.** If they diverge, a contributor can
follow the official local process, get green, and still break CI — which is exactly what this
skill exists to prevent. Any PR that changes the CI toolchain updates this file in the same PR.

## Python steps

1. **Install the locked toolchain.** CI installs from `uv.lock`, not from `pyproject.toml`'s
   lower bounds, so a green run stays green. `uv` itself is pinned for the same reason.
   ```bash
   pip install "uv==0.8.17"
   uv sync --locked --extra dev
   ```
   Every following Python command runs through `uv run` so it uses that environment rather than
   whatever is on `PATH`.

2. **Lint** — same scope as CI (`apps`, `services` and `scripts`):
   ```bash
   uv run ruff check apps services scripts
   ```
   If it fails, fix the findings (`--fix` for the auto-fixable ones) and re-run. Never widen or
   disable a rule to pass without saying so.

3. **Tests + coverage gate** (CI gates at 90%; baseline is ~97%):
   ```bash
   uv run pytest apps services -q --cov=apps --cov=services --cov-report=term-missing --cov-fail-under=90
   ```
   If coverage drops a new file below the line, add tests rather than lowering the gate.

## Frontend steps

Skip these only if the diff touches no TypeScript, no `apps/*/ui`, and no API response model —
a backend contract change breaks the generated client, so step 4 matters even for Python-only
diffs.

4. **Generated types are in sync.** The TypeScript client is generated from the API's OpenAPI
   schema and never hand-written (ADR-0001). Regenerating must be a no-op:
   ```bash
   pnpm install --frozen-lockfile
   uv run pnpm run codegen
   git status --porcelain -- schemas/openapi.json apps/fta/ui/src/api/schema.ts
   ```
   Any output means the committed types have drifted — commit the regenerated files.
   `--porcelain`, not `git diff`, because it reports untracked files too.

5. **Frontend lint, types, tests, build:**
   ```bash
   pnpm -r --if-present lint
   pnpm -r --if-present typecheck
   pnpm --filter @inzbc/fta-ui run coverage   # gate: 80%
   pnpm -r --if-present build
   pnpm --filter @inzbc/fta-ui run build-storybook
   ```
   `typecheck` catches things the tests do not — strict options like
   `noUncheckedIndexedAccess` fail there and nowhere else.

   The Storybook step is a **compile check**. It proves the stories and config build; it does
   **not** run the a11y addon's checks. Do not report it as accessibility evidence.

## Before pushing

6. **Secret scan** (repo rule — never commit `.env*` or credentials):
   ```bash
   docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:latest detect --source /repo --no-git --redact
   ```
   If Docker isn't available, scan the staged diff by pattern and say so in the evidence block —
   CI's gitleaks job is blocking and will run regardless.

7. **Review what is staged.** `git status --short` after any broad `git add`. Build artifacts
   (`coverage/`, `storybook-static/`, `*.egg-info/`, `dist/`, `.venv/`) must not be committed;
   they are gitignored, but a stale one can still be tracked from an earlier commit.

8. **Emit the PR evidence block** with the real command output pasted in, matching
   `docs/workstreams/README.md`:
   ```
   ## Evidence
   - Task: <worklog item>
   - Reused: <existing helpers/types reused, or "none — searched, none fit">
   - Sources: <docs/URLs used, or "n/a">
   - Checks: ruff / pytest+coverage / type drift / frontend / secret scan  (paste the output)
   - Review: self-reviewed; adversarial review if security-touching
   - Watch closely: <the 1-2 things the reviewer should look hardest at>
   ```

## Rules

- Do not open a PR while any step is red. Report the failure instead.
- Keep pinned versions equal to CI (`uv`, `ruff`, `setuptools`); a mismatch is how
  green-locally-red-in-CI happens.
- Cross-lane changes need a `SHARED-OK:` note recorded in **both** worklogs
  (`docs/workstreams/`), not just a mention in the PR body.
- **No AI attribution in PRs, commits or code** (`CLAUDE.md`, `CONTRIBUTING.md`). If a tool
  appends an attribution footer to a PR body, edit the PR to remove it.
- Security-touching changes (auth, gateway, redaction, verification gates) get an adversarial
  self-review before the PR, per the repo quality standard.
- This is a checking skill — it does not push, merge, or open the PR itself unless asked.
