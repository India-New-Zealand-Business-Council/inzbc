# Contributing

## Branches and PRs
- **No direct pushes to `main`.** Branch, then open a pull request.
- Branch names: `feat/…`, `fix/…`, `chore/…` in short kebab-case.
- PRs are reviewed and merged by the tech lead (Bhanu). Everyone else opens PRs.
- Keep PRs small and focused: one concern each.

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
