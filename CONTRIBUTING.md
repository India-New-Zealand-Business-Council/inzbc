# Contributing

## Branches and PRs
- **No direct pushes to `main`.** Branch, then open a pull request.
- Branch names: `feat/…`, `fix/…`, `chore/…` in short kebab-case.
- PRs are reviewed and merged by the tech lead (Bhanu). Everyone else opens PRs.
- Only `@bhanuGupta1` can satisfy required code-owner approval or merge into `main`.
  GitHub still permits collaborators to leave feedback; their approval does not replace the
  tech lead's. Only the tech lead can dismiss reviews. His own PRs use the owner-only PR bypass
  when needed, because GitHub forbids self-approval.
- Keep PRs small and focused: one concern each.
- **Rebase, never merge `main` into a branch.** To catch up, run `git fetch origin main` and then
  `git rebase origin/main`, then `git push --force-with-lease`. A "Merge main into …" commit is not
  allowed, and neither is GitHub's "Update branch" button in its merge mode. Force-push only a
  branch you own.
- **Stacked PRs:** once the lower PR lands, rebase the upper branch onto `main` with
  `git rebase --onto origin/main <lower-branch>` and retarget the PR to `main`. Do not merge
  `main` or the lower branch into it.
- **`main` stays linear.** Land PRs with "Rebase and merge", never "Create a merge commit". Use
  "Squash and merge" only when a branch's own commits are not worth keeping.

## Process decisions

- Changes to review ownership, review rotations, team reporting requirements or working cadence
  require the tech lead's explicit approval before adoption. Client-controlled decisions still
  require the client's approval under `PROJECT-RULES.md`.
- Use the process-change issue form to propose a change. Opening an issue, assigning an action,
  or recording a proposal in standup notes does not make it agreed. Link the approving decision
  before describing a change as accepted or scheduling mandatory team work under it.
- Label proposals and unconfirmed meeting statements clearly. Correct inaccurate activity
  records against timestamped evidence; do not infer attendance or inactivity from missing replies.

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
Do not edit or publish `inzbc.org`. Build on the duplicate site (`docs/discovery.md` OI-9);
go-live needs Sunil's written sign-off and is his to press. Log every Wix editor session in
`docs/wix-changes-log.md`. Full rules in [PROJECT-RULES.md](./PROJECT-RULES.md).
