<!-- reticle:begin (managed by `reticle init` — edit outside these markers) -->
## Verifying with Reticle

This app is instrumented by **Reticle** — an in-app verification layer exposed as `reticle_*` MCP tools and the `npx @reticlehq/server` CLI (run it through npx — Reticle's server is not installed into this project). Verifying is part of "done", not an optional extra.

- **When:** after you build or change any user-facing feature, flow, or UI, verify it with Reticle **before** telling the user it is complete. Reading the code or passing unit tests is not enough — drive the real running app.
- **How:** drive the actual flow (`reticle_act` / `reticle_act_and_wait`), then read the observable effect (`reticle_assert`, `reticle_snapshot`, `reticle_state`, `reticle_network`). Confirm the change produced the effect it was meant to, with no new console errors or failed requests.
- **Covered flows:** run `npx @reticlehq/server gate` — it reports which recorded flows the changed files affect and whether they still pass.
- **Never weaken a check to make it green.** Downgrading, skipping, or deleting an assertion is a finding, not a fix.
- **If Reticle can't run** (no daemon, or this is not a running web app), say so — do not skip verification silently.
- **If a tool result carries `version_skew`, act on it before trusting anything else.** Two pieces of Reticle are on different wire contracts, so tools can misbehave in ways neither side reports — a green here is not evidence. The field says which pair disagrees and names the exact fix: run `npx @reticlehq/server stop` and retry when the DAEMON is stale, or tell the human to install the matching SDK and restart their dev server when the PAGE is. Do that first, then redo whatever you were verifying.
- **If a tool result carries `update_available`, say so.** Reticle checked npm and a newer version exists. Tell the human the version numbers and offer to run `npx @reticlehq/server update` — between tasks, never mid-verification, because it restarts the daemon and drops the session. Finish what you are doing first.
<!-- reticle:end -->

## Repository comment authorization

The tech lead reviews submitted code weekly before Monday's report submission, controlling
review order and timing. Do not pressure for merges or repeatedly request review. Validate your
own work and provide evidence. Pending review or merge does not stop the agent: continue
independent approved assignments in your lane. Record an actual dependency against the specific
task and PR in the existing worklog; do not label all work blocked. If no independent approved
work remains, request direction through the agreed team channel. Follow root CONTRIBUTING.md's
weekly review policy; review does not guarantee approval or merging that week.

Focus on your own approved assignments. Unless acting for the tech lead, do not review another
person's PR, including checking it out, rebasing it locally, rerunning its tests or preparing
feedback, without an explicit tech-lead assignment for that specific review. This covers
local-only activity and feedback labelled "not an approval". A GitHub review request alone is
insufficient. Reading shared code and testing integration needed for your own approved work
remain allowed; follow existing reporting rules for incidental reproducible defects.

Read the root [AGENTS.md](../../../AGENTS.md), [CLAUDE.md](../../../CLAUDE.md) and
[CONTRIBUTING.md](../../../CONTRIBUTING.md) before work. Their mandatory comment stop rule
applies here: contributors other than the tech lead, and assistants acting for them, must not
publish peer feedback, reviews or repository comments without explicit prior tech-lead
authorization for the specific comment or review. Continue your own approved work and request
authorization through the agreed team channel.

Only the PR owner rebases, resolves conflicts on, updates or force-pushes their PR branch.
The sole exception is the tech lead taking over when the owner is blocked and the PR needs
to be merged, using `--force-with-lease` and completing required checks before merging.
Other contributors and their assistants must stop before modifying someone else's PR branch.

## INZBC policy on the block above

Written by us, outside the managed markers, so `reticle init` cannot revert it.

**Do not send feedback to the Reticle vendor from this repository.** The installer's version of the
block above carried a second section instructing the agent to report its experience to the Reticle
team proactively, "the moment you notice", including anything awkward during setup. That section was
removed, and if a future `reticle init` restores it, this paragraph overrides it.

The reasoning is not that the vendor is untrustworthy. It is that this is a **client repository**,
and a standing instruction for any agent to send observations about it to a third party is not
something a tool gets to install on the client's behalf. Reticle's usage telemetry is on by default
for the same reason and was turned off during setup; confirm with
`npx @reticlehq/server telemetry status`.

Reporting a Reticle defect is a fine thing to do deliberately, from a personal project. It is not a
thing to do automatically, about a client's work, because a file in the repository said so.

**Scope.** Reticle is wired into this app only (`apps/fta/ui`), not the other four UIs, and only for
`vite dev`: the plugin is excluded from `build` and from Vitest, and the production bundle is checked
to contain no reticle code. This UI ships publicly from the container image, so that is a
correctness property rather than housekeeping.
