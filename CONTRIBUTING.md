# Contributing

Tech lead: Bhanu Gupta (`@bhanuGupta1`). This role is the approval authority referenced below.

## Branches and PRs
- **No direct pushes to `main`.** Branch, then open a pull request.
- Branch names: `feat/…`, `fix/…`, `chore/…` in short kebab-case.
- PRs are reviewed and merged by the tech lead. Everyone else opens PRs.
- Only the tech lead can satisfy required code-owner approval or merge into `main`.
  Contributor comments and peer feedback are prohibited unless explicitly authorized as described
  below. Only the tech lead can dismiss reviews. The tech lead's own PRs use the owner-only PR bypass
  when needed, because GitHub forbids self-approval.
- Keep PRs small and focused: one concern each.
- **Rebase, never merge `main` into a branch.** To catch up, run `git fetch origin main` and then
  `git rebase origin/main`, then `git push --force-with-lease`. A "Merge main into …" commit is not
  allowed, and neither is GitHub's "Update branch" button in its merge mode.
- **Only the PR owner rebases their branch.** Other contributors and their assistants must not
  rebase, resolve conflicts on, update or force-push someone else's PR branch. The only exception
  is the tech lead taking over when the PR owner is blocked and the PR needs to be merged.
  That exception permits the tech lead to rebase, resolve conflicts and push with
  `--force-with-lease`, then complete the required checks before merging. It does not authorize
  other contributors to take over. This ownership rule also applies to stacked PRs and GitHub's
  branch-update controls.
- **Stacked PRs:** once the lower PR lands, rebase the upper branch onto `main` with
  `git rebase --onto origin/main <lower-branch>` and retarget the PR to `main`. Do not merge
  `main` or the lower branch into it.
- **`main` stays linear.** Land PRs with "Rebase and merge", never "Create a merge commit". Use
  "Squash and merge" only when a branch's own commits are not worth keeping.

## Weekly review and work awaiting review

- The tech lead reviews submitted code each week before Monday's report submission. The tech
  lead controls review order and timing around other project responsibilities and the amount of
  code requiring verification. This is a review cadence, not a promise to approve or merge every
  PR that week. Late submissions or unresolved findings may carry into the next review cycle.
- Do not pressure the tech lead to merge, impose personal review deadlines, repeatedly request
  reviews, or treat an open PR as permission to bypass checks or approval. A green CI run alone
  does not establish that the code works or is ready to merge.
- The PR author owns correctness, self-review, reproducible test evidence and fixing findings,
  including for AI-assisted code. Submit focused PRs with evidence so the tech lead can verify
  behavior, integration and security. Review is not a substitute for the author's validation.
- **Awaiting review is not a blanket work blocker.** Contributors and their assistants must
  continue the next independent, already approved assignment in their lane while a PR awaits
  review or merge. Do not stop an agent run merely because a PR has been opened. Do not start
  unapproved work, unsolicited peer review or changes to someone else's branch to stay busy.
- If a particular task genuinely depends on an unmerged change, record the affected task, PR
  and concrete dependency in the existing worklog. Describe the PR as "awaiting tech-lead
  review" and only that dependent task as blocked; continue other approved independent work.
  If none remains, report the specific dependency and request direction through the agreed
  team channel. Do not invent progress, repeatedly ping for a merge or create another issue
  merely to escalate review timing. Existing urgent security/incident procedures still apply.

## Comments and peer feedback: mandatory stop rule

- **Focus on your own approved assignments. Unassigned peer review is prohibited.** Contributors
  other than the tech lead, and assistants acting for them, must not spend project time auditing,
  checking out, locally rebasing, rerunning tests for, or preparing reviews of another person's
  PR unless the tech lead explicitly assigns that specific review beforehand. Calling it
  "peer feedback, not an approval" does not exempt it. A GitHub review request or mention alone
  is not an assigned review. Local-only review activity is covered even if nothing is pushed.
- Reviewing shared code needed for your own approved implementation and testing that work's
  integration remain part of your assignment. Do not expand that into a separate peer-review
  exercise. If you incidentally discover a reproducible defect, preserve the evidence and follow
  the existing reporting rules; do not start an unsolicited audit of someone else's work.
- Only the tech lead may publish repository comments or PR reviews by default. All other
  contributors and their assistants must stop before submitting peer feedback, review summaries,
  inline review comments, approvals, requests for changes, or comments on PRs, issues, commits
  and repository discussions. This includes comments on their own PRs and issues.
- An exception requires explicit prior tech-lead authorization for the specific comment or
  review. An assignment, review request, mention, existing conversation or available GitHub
  permission does not authorize commenting. Do not substitute a new issue for prohibited feedback.
- Request authorization and send findings through the existing agreed team channel. Continue
  your own approved implementation work while awaiting a decision. Do not begin an unassigned
  review or prepare unsolicited review findings locally while waiting.
  Opening assigned PRs and reporting reproducible defects under the issue rules remain allowed.
- This is a mandatory contributor and assistant instruction. It does not disable GitHub's
  comment controls or revoke collaborators' platform permissions. Branch review requirements
  govern approval and merging; they do not prevent a collaborator from posting a comment.

## Process decisions

- Only the tech lead authorizes scope, priorities, assignments, repository governance, team
  process, recurring reporting, additional ceremonies and review arrangements. Contributors
  execute approved assignments in their existing lanes and report reproducible defects with
  evidence. Additional work or obligations require prior explicit tech-lead authorization.
  Existing client approval gates and the documented team meeting cadence remain in effect.
- Changes to review ownership, review rotations, team reporting requirements or working cadence
  require the tech lead's explicit approval before adoption. Client-controlled decisions still
  require the client's approval under `PROJECT-RULES.md`.
- Obtain the tech lead's explicit authorization **before opening** a new issue or board item
  for reporting duties, attendance tracking, review rotations, retrospectives, recurring board
  maintenance, workload reassignment or other team-process changes. Link that authorization
  in the process-change form. Request a decision first through the agreed team channel, or an
  existing relevant discussion where the tech lead has explicitly authorized the comment.
- Search for duplicates before opening any issue. Do not recreate rejected issues #320 or #405
  or equivalent replacements without explicit tech-lead approval.
- Opening an authorized proposal, assigning an action,
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
