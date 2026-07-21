# INZBC Digital Platform

Digital platform for the India New Zealand Business Council (INZBC): a new website plus three
AI-supported tools. Delivered as an AIC / Otago Polytechnic placement (Bhanu Gupta, Roshan
Aryal, Paras).

## Scope
Four confirmed modules:
1. **Website** — a new, separate site (built on Wix), cut over to inzbc.org at go-live.
2. **AI Communications Assistant** — drafting for newsletters, events, posts. Adversarially
   tested before staff use.
3. **FTA Opportunity Explainer** — sourced, guided assistant on the NZ/India FTA.
4. **Trade Intelligence Digest / SIP** — weekly, human-reviewed intelligence platform.

## Status
Discovery / early build. Nothing is in production. All automation and AI publishing stays
disabled behind human review (`production_enabled = false`).

## Repository layout
```
docs/            planning and specs (committed)
  discovery.md         site audit, IA, open-items register
  page-specs.md        per-page content specs for the new site
  fta-source-corpus.md FTA Explainer source list and rules
  sip/                 Trade Intelligence Platform spec + config
```
Internal/personal docs (client comms, services agreement) are gitignored, kept local.

## The live site
`inzbc.org` runs on Wix and is **not** edited directly. The new site is built separately and
only replaces the live one at go-live, after backup and explicit sign-off. Wix MCP writes hit
live data instantly, so they are not used against the live site.

## Working on this repo
See [CONTRIBUTING.md](./CONTRIBUTING.md). Short version: branch, open a PR into `main`, no
direct pushes to `main`.
