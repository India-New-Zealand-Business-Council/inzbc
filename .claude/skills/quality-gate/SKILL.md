---
name: quality-gate
description: >
  Run the INZBC repo's pre-PR quality gate and produce the PR evidence block. Use before
  opening or updating any pull request in this repo, or whenever the user asks to "run the
  checks", "run the quality gate", "check before PR", or "generate the evidence block". Mirrors
  the CI jobs (ruff, pytest+coverage, secret scan) so failures are caught locally first.
---

# Quality gate

This repo's definition of "Done" is: lint, typecheck-equivalent, and tests all pass, plus a PR
evidence block (see `docs/workstreams/README.md`). This skill runs those checks the same way CI
does and formats the result, so a PR is never opened red.

## Steps

1. **Install the pinned toolchain** (match CI — do not use a floating ruff; the pin lives in
   the root `pyproject.toml`):
   ```bash
   pip install -e ".[dev]"
   ```

2. **Lint** — same scope as CI (`apps` and `services`):
   ```bash
   ruff check apps services
   ```
   If it fails, fix the findings (`ruff check --fix apps services` for the auto-fixable ones)
   and re-run. Never widen or disable a rule to pass without saying so.

3. **Tests + coverage gate** (CI gates at 90%; baseline is ~97%):
   ```bash
   pytest apps services -q --cov=apps --cov=services --cov-report=term-missing --cov-fail-under=90
   ```
   If coverage drops a new file below the line, add tests rather than lowering the gate.

4. **Secret scan** before pushing (repo rule — never commit `.env*` or credentials):
   ```bash
   docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:latest detect --source /repo --no-git --redact
   ```
   If Docker isn't available locally, run `pre-commit run gitleaks --all-files` instead.

5. **Emit the PR evidence block** with the real command output pasted in, matching
   `docs/workstreams/README.md`:
   ```
   ## Evidence
   - Task: <worklog item>
   - Reused: <existing helpers/types reused, or "none — searched, none fit">
   - Sources: <docs/URLs used, or "n/a">
   - Checks: ruff / pytest+coverage / secret scan  (paste the output)
   - Review: self-reviewed; adversarial review if security-touching
   - Watch closely: <the 1-2 things the reviewer should look hardest at>
   ```

## Rules

- Do not open a PR while any step is red. Report the failure instead.
- Keep the local ruff version equal to the CI pin (`.github/workflows/ci.yml`); a mismatch is
  how green-locally-red-in-CI happens.
- Security-touching changes (auth, gateway, redaction, verification gates) get an adversarial
  self-review before the PR, per the repo quality standard.
- This is a checking skill — it does not push, merge, or open the PR itself unless asked.
