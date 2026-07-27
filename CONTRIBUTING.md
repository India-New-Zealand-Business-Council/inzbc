# Contributing

## Branches and PRs
- **No direct pushes to `main`.** Branch, then open a pull request.
- Branch names: `feat/…`, `fix/…`, `chore/…` in short kebab-case.
- PRs are reviewed and merged by the tech lead (Bhanu). Everyone else opens PRs.
- Keep PRs small and focused: one concern each.

## The project board
- **Never call `updateProjectV2Field` directly.** It replaces a single-select field's whole option
  set, and an item's value points at an option *id*, not its name. Re-sending the same option names
  still mints new ids and silently blanks that field on every item. This has happened twice.
- Use `python scripts/board.py add-option <field> "<name>"`, which snapshots, mutates, restores and
  verifies. `snapshot`, `restore` and `verify` are available separately.
- Take a snapshot before any bulk board edit: `python scripts/board.py snapshot`.
- Writing a bulk edit by hand? Check the exit code of every call and count failures. A loop that
  pipes `gh` errors away will report success after failing every single time.

## Commits
- Imperative subject under ~60 chars that names the real change.
- Body only when the diff cannot explain why.
- No AI attribution in commits, PRs, or code comments.

## Don't commit
- Secrets, `.env*`, API keys, credentials. Run a secret scan before pushing.
- Generated output or local-only files.
- Client-confidential or personal docs (already gitignored).

## Content standards (public-facing work)
- Executive tone: professional, data-driven, politically neutral.
- Never invent statistics, board names, or FTA details. Sourced material only.
- Every AI-drafted output needs a named human reviewer before publishing.
- Handle member/personal data per the NZ Privacy Act 2020.

## The live site
Do not edit `inzbc.org` directly. Build in the separate site; go-live needs backup and sign-off.
