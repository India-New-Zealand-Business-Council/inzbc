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

## Editing the project board

Never call `updateProjectV2Field` directly. It replaces a single-select field's whole option set and
orphans every item's value. Use `python scripts/board.py add-option <field> "<name>"`. See
[CONTRIBUTING.md](./CONTRIBUTING.md).
