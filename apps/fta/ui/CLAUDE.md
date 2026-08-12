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
