# Issue and project-board authorization

AI assistance is allowed under the existing project rules. It does not confer authority to
create team obligations or change the review process.

Only the tech lead may authorize scope, priorities, assignments, repository governance,
team process, recurring reporting, additional ceremonies and review arrangements.
Contributors execute approved assignments in the existing lanes and report reproducible
defects with evidence. Additional work or obligations require prior tech-lead authorization.

- Before creating any issue or board item, search existing issues for the same work. Do not
  create duplicate, stale-backlog or speculative administrative issues.
- Clarification questions, permission requests and meeting invitations belong in the existing
  work discussion or agreed team channel. Do not create a standalone question-only issue or
  board item unless the tech lead explicitly authorizes it as tracked work. Record related
  answers together; do not turn each answer into another issue.
- New issues or board items for daily reporting, attendance tracking, review rotations,
  retrospectives, recurring board duties, workload reassignment or other team-process changes
  require explicit prior authorization from the tech lead (defined in CONTRIBUTING.md). Include its link.
- Without that authorization, stop the issue/board action and request a decision in the existing
  relevant discussion. Do not open another issue to manufacture the required authorization.
- Do not reopen or recreate rejected process issues, including #320 and #405, without
  the tech lead's explicit approval. Do not infer approval from a plan, milestone or standup note.
- Only the tech lead approves contributor PRs and merges into `main`. Peer feedback does not
  replace that approval. Do not introduce a review rota or change approval ownership.
- Do not edit runtime `.env` files or credentials. A human configures them locally. Never
  commit secrets or include personal/client data in issue bodies or tool prompts.

These instructions apply to contributors and their assistants. Repository files cannot enforce
tool behavior on other computers; GitHub rules enforce the merge restrictions. Read
[CONTRIBUTING.md](./CONTRIBUTING.md) and [PROJECT-RULES.md](./PROJECT-RULES.md).

# Running this repo

Read this before running tests or lint. Getting the interpreter wrong produces failures that look
like real defects and are not.

## Always run through `uv`

```
uv sync --locked --extra dev     # once, and after any dependency change
uv run python -m pytest apps services -q
uv run ruff check apps services scripts
```

**Do not run a bare `python` or `pytest`.** `pyproject.toml` sets `requires-python = ">=3.11"`, and
the interpreter first on `PATH` is often older. On Python 3.10 the suite reports one failure,
`test_parse_published_at_handles_gdelt_seendate`, because `datetime.fromisoformat` did not parse a
trailing `Z` until 3.11. That test is correct and passes on a supported interpreter. Reading it as a
defect, or as evidence that the environment lacks `pytest` or `pydantic`, is a wrong conclusion that
has already been drawn once.

`--locked` installs the resolution in `uv.lock` rather than re-resolving, so a green run stays green:
`pyproject.toml` carries lower bounds only, and an unrelated upstream release would otherwise change
what you are testing with no commit here. `--extra dev` is what brings in `pytest`, `pytest-cov` and
`ruff`; `uv run --frozen` alone installs the runtime dependencies only and leaves you without them.

## Running shell commands on Windows

The team develops on Windows, where the shell is **PowerShell 5.1**. Two things bite, both verified
here rather than assumed:

- **`&&` and `||` are parser errors**, not just unsupported. `echo a && echo b` fails on the token
  itself. Use `A; if ($?) { B }`, or run the commands separately.
- **Quote any path built from an environment variable.** `Set-Content $env:TEMP\x.py` silently
  writes somewhere other than where you then read from; `Set-Content -Path "$env:TEMP\x.py"` works.

Here-strings **do** work, provided the outer quoting is right:
`-Command "@'` ... `'@ | python -"` with double quotes outside and single inside.

Installing PowerShell 7 does not help, and makes things worse for sandboxed tooling. `winget` ships
it as MSIX, whose only entry point is a Store execution alias under `WindowsApps`. Sandboxed
processes cannot spawn that path (`CreateProcessAsUserW failed: 5, Access is denied`), so the shell
stops working entirely. This was tried and reverted. An MSI build installing to
`C:\Program Files\PowerShell\7` would be fine, but that is not what `winget` provides.

## What CI runs

`.github/workflows/ci.yml` is the authority. In short: ruff, pytest with a 90% coverage gate,
generated-type drift, frontend lint/typecheck/test/build, Storybook compile, Semgrep, gitleaks,
actionlint, link check, a Docker image build with endpoint smoke tests, and a linked-issue check.

```
uv run pytest apps services -q --cov=apps --cov=services --cov-fail-under=90
```

The frontend needs `pnpm install --frozen-lockfile` first; Node version comes from `.nvmrc`.

## Frontend

```
pnpm install --frozen-lockfile
pnpm --filter @inzbc/fta-ui run test
pnpm --filter @inzbc/fta-ui run build
```

`apps/fta/ui/src/api/schema.ts` is generated from `schemas/openapi.json` and never edited by hand.
Run `uv run pnpm run codegen` and commit the result; CI fails if regenerating changes anything.

## Things that are deliberate, not bugs

- **`GET /api/source-library` and the other SIP endpoints return 404.** `services/api` serves only
  `/api/fta/query` and `/health` today. `apps/sip/pipeline/client.py` is written against the
  published contract in `schemas/api-contract.md` ahead of the server, which ADR-0004 describes.
- **`source_library.name` is not unique.** Both New Zealand and India have a "Ministry of Defence"
  and a "Ministry of Education" in `apps/sip/collector/data/sip185_sources_v1.0.csv`. Resolve source
  checks by `sip185_code`, never by name. An ambiguous name must degrade to unset rather than pick a
  row.
- **`production_enabled` is `false` everywhere**, and nothing AI-drafted publishes without a named
  human reviewer. See [PROJECT-RULES.md](./PROJECT-RULES.md).

## Keeping branches current

Rebase, never merge. Bring a branch up to date with `git rebase origin/main`, not
`git merge main`. For a stacked PR whose lower PR has landed, use
`git rebase --onto origin/main <lower-branch>`. Then push with `--force-with-lease`. Land PRs with
"Rebase and merge" so `main` stays linear, and never create a merge commit. See
[CONTRIBUTING.md](./CONTRIBUTING.md).

## Editing the project board

Never call `updateProjectV2Field` directly. It replaces a single-select field's whole option set and
orphans every item's value. Use `python scripts/board.py add-option <field> "<name>"`. See
[CONTRIBUTING.md](./CONTRIBUTING.md).
