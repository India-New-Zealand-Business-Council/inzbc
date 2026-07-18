# AI Service Layer — Architecture Spike

Status: draft for review (Discovery). Decides how the three AI modules integrate with the
new Wix site so Phase 2/3 aren't blocked on this later.

> **Assumptions stated up front** (verify once Wix MCP is connected — see Open Questions):
> - The site presentation layer is **Wix** (client-confirmed).
> - Wix Velo offers: backend web modules, scheduled jobs, a Secrets Manager, and Wix Data
>   (CMS) collections queryable from front end and backend. Exact limits (job frequency,
>   execution timeouts, outbound request caps) are **unconfirmed** and gate part of this design.

---

## The three modules and what they actually are

| Module | Nature | Audience | Needs |
|--------|--------|----------|-------|
| AI Communications Assistant | RAG + LLM drafting | **Internal staff** | Vector store over INZBC content, Claude API, must pass adversarial security review before staff use |
| FTA Opportunity Explainer | Guided, sourced Q&A | **Public / members** | Curated FTA source corpus, LLM with citations, embedded on Trade Resources |
| Trade Intelligence Digest | Scheduled pipeline + archive | Pipeline internal; **archive public** | Source evaluation, LLM summarisation, **human review gate**, weekly cadence, archive pages |

Key insight: only the FTA Explainer *must* live visually inside the site. The Comms
Assistant is a staff tool (better isolated — also makes the required security review
cleaner). The Digest is a backend pipeline whose only public surface is the archive.

---

## Options considered

**A — All-in Wix Velo.** Build every backend in Velo; data in Wix collections; digest on a
Velo scheduled job. *Pro:* one platform, MCP-buildable, native CMS. *Con:* Velo backend
constraints (timeouts, no long-running work, awkward vector search), secrets tied to Wix,
harder local testing → weakens the mandated adversarial security review of the Comms Assistant.

**B — Wix front + external service (recommended).** Wix hosts pages + the digest archive
(Wix CMS). A separate service **in this git repo** runs the RAG, FTA Explainer API, and the
scheduled digest pipeline. *Pro:* AI/RAG unconstrained; code is version-controlled and
**testable/security-reviewable** (directly satisfies the Comms Assistant review requirement);
human-review gate maps to a Wix CMS draft/approved status. *Con:* two systems to run; needs a
host + secret storage for the service.

**C — Fully external, Wix just links out.** Simplest, but disjointed UX and no integration.

---

## Recommended architecture — Option B (hybrid)

```
                         ┌─────────────────────────── Wix site (presentation) ───────────────────────────┐
                         │  Marketing pages   Trade Resources        Digest page + Archive                │
                         │                    └─ embeds FTA Explainer └─ renders Wix CMS (status=published)│
                         └──────────▲───────────────────▲───────────────────────▲──────────────────────────┘
                                    │ iframe/custom elem │ fetch                 │ Wix Data (read published)
                                    │                    │                       │
        ┌───────────────────────────┴────────────────────┴───────────────────────┴───────────┐
        │                AI Service (this repo — hosted separately, own secrets)               │
        │   ┌────────────────┐   ┌────────────────┐   ┌──────────────────────────────────┐    │
        │   │ Comms Assistant│   │ FTA Explainer  │   │ Digest pipeline (scheduled)      │    │
        │   │ (staff-only)   │   │ API + citations│   │ evaluate sources → summarise →   │    │
        │   │ RAG + Claude   │   │ RAG + Claude   │   │ write DRAFT to Wix CMS           │    │
        │   └────────────────┘   └────────────────┘   └──────────────┬───────────────────┘    │
        └───────────────────────────────────────────────────────────┼────────────────────────┘
                                                                     │ Wix Data API (write draft)
                    Named human reviewer approves in Wix dashboard  ▼  draft → published
```

- **Comms Assistant:** standalone staff tool, **not** on the public site. Isolation makes the
  required adversarial/security review self-contained. Ships only after that review passes.
- **FTA Explainer:** external API, embedded on the Trade Resources page via Wix custom element
  / iframe. Answers cite their source corpus (no invented FTA details).
- **Digest:** scheduled job in the service generates a **draft**, writes it to a Wix CMS
  collection with `status = draft`. A **named reviewer** edits/approves in the Wix dashboard,
  flipping `status = published`. The public Digest page + archive render **only** published
  items. This is the proposal's human-review commitment expressed as a data gate, not a bypass.

### Why this fits the brief
- LLM/RAG code lives in the repo → real test harness → the Comms Assistant security review is
  meaningful (matches Bhanu's security-testing role, kept explicit).
- Site still "built on Wix" as the client intends.
- Human-review-before-publish is structural (CMS status), impossible to silently automate past.

---

## Open questions (resolve when Wix MCP is connected / with the team)

1. **Velo limits** — do scheduled jobs, Secrets Manager, and Wix Data write-from-external-API
   meet the digest gate? If Wix Data can't be written from an outside service cleanly, the
   digest may instead push via a small Velo webhook. Confirm at build time.
2. **Hosting for the AI service** — **constraint (client): keep the frontend on Wix, and
   prefer free-tier hosting + free web-search for the digest's source-gathering.** Candidate
   free tiers to evaluate: Cloudflare Workers, Fly.io free allowance, Render free web service,
   Deno Deploy, GitHub Actions (for the scheduled digest job — free cron, no always-on host).
   Free web-search options to evaluate for source-gathering: DuckDuckGo, Brave Search API free
   tier, RSS feeds from evaluated public sources. Claude API key still needs secret storage.
   **User approval required before provisioning anything.** (Note: only Claude API usage is a
   likely paid line item; hosting + search targeted to free tiers.)
3. **FTA source corpus + Comms/RAG corpus** — which official documents are in scope, and who
   is the named reviewer (OI-5)?
4. **Member Jungle / Mailchimp** (see discovery.md OI-7) — does the Comms Assistant draft
   *into* Mailchimp, or just produce copy for staff to paste?

No infrastructure is provisioned and no packages are installed by this document — it is a
design proposal only.
