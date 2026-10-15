# Project instructions

Read [AGENTS.md](./AGENTS.md), [CONTRIBUTING.md](./CONTRIBUTING.md) and
[PROJECT-RULES.md](./PROJECT-RULES.md) before work.

AI assistance is allowed. Before any issue or board action, enforce the authorization rules
in AGENTS.md: no new team-process issues or recurring obligations without prior explicit
tech-lead authorization. Stop unauthorized actions. Do not recreate rejected #320/#405 or
introduce a review rota. Only the tech lead provides required contributor PR approval and merges.
Only the tech lead authorizes scope, priorities, assignments, process and review arrangements.
Keep clarification questions and invitations in the agreed team channel, or an existing discussion
where the tech lead has explicitly authorized the comment.
Do not open question-only issues or board items without explicit tech-lead authorization.
Work within approved assignments; obtain authorization before creating additional work or duties.

The tech lead reviews submitted code weekly before Monday's report submission and controls
review order and timing; approval or merge that week is not guaranteed. Do not pressure for a
merge, impose review deadlines or repeatedly request review. Validate your own code, including
AI-assisted code, and provide reproducible evidence; green CI alone is insufficient.
Do not end work merely because a PR awaits review or merge: continue independent, already
approved assignments in your lane. Record "awaiting tech-lead review" for the PR. Mark only a
specific dependent task blocked, with its PR and concrete dependency in the existing worklog.
If no independent approved work remains, report it and request direction through the agreed
team channel; do not invent work or create review-escalation issues. See CONTRIBUTING.md's
weekly review policy; existing urgent security/incident procedures still apply.

Mandatory stop before unassigned peer review: unless acting for the tech lead, focus on your own
approved assignments. Do not audit, check out, locally rebase, rerun tests for, or prepare reviews
of another person's PR without the tech lead explicitly assigning that specific review first.
This includes local-only activity and "peer feedback, not an approval". A GitHub review request
or mention alone is not an assignment. Read shared code and test integration as needed for your
own approved work; report incidental reproducible defects under the existing rules.

Mandatory stop before publishing comments or reviews: unless acting for the tech lead, do not
submit peer feedback, approvals, requests for changes, inline review comments, or comments on
PRs, issues, commits or repository discussions (including your own work) without explicit prior
tech-lead authorization for the specific comment or review. Assignments, review requests, mentions
and GitHub permissions do not authorize this. Continue your own approved work; request authorization
through the existing agreed team channel. Do not open a replacement issue to bypass the rule.
Follow CONTRIBUTING.md's "Comments and peer feedback" section. This instruction does not disable
GitHub comment controls.

Do not edit runtime environment files or disclose credentials, personal data or client data.

Only the PR owner rebases, resolves conflicts on, updates or force-pushes their PR branch.
Stop before modifying another contributor's PR branch. The sole exception is the tech lead
taking over when the owner is blocked and the PR needs to be merged; use `--force-with-lease`
and complete required checks before merging. Follow CONTRIBUTING.md for stacked PRs and
branch-update controls as well.
