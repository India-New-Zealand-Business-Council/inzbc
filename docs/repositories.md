# The three repositories, and how to work across them

INZBC's system spans three repositories. They are deliberately separate, and that separation keeps
causing the same practical problem: an agent or a person opens one, does good work, and never learns
the other two exist.

This page is the fix for the knowledge half. `--add-dir` is the fix for the tooling half.

---

## What each one holds

| Repository | Holds | Who writes to it |
|---|---|---|
| **`inzbc`** | The platform. Shared API contract, database schema, SIP core, FTA Explainer, Comms Assistant, and **every controlled document**. This is the source of truth for decisions | The team, through reviewed pull requests |
| **`daily-india-nz-news-agent`** | The SIP collection engine. A scheduled Python service that reaches untrusted external sources and produces **draft output only**. It cannot distribute and it cannot approve | The team, through reviewed pull requests |
| **`inzbc-studio-site`** | The Wix Studio website. Site code, page code, backend modules, public files | The team **and Wix**. The Wix GitHub App and the Wix CLI both push here |

That third row is the reason all three stay separate rather than becoming one repository.

---

## Why not one repository

Asked and answered, so it is not re-litigated every few weeks.

**Wix owns the structure of the site repository.** The Studio Git integration creates the repository
itself, scaffolds its own layout at the root, and pushes to it from the GitHub App and the CLI. It
cannot be a subdirectory of something else, and a subtree merge would fight Wix's own pushes.

**Blast radius.** Connecting Wix installs a GitHub App with write access. Pointing that at `inzbc`
would give a third-party integration write access to the shared contracts, the database schema, the
decision model and the secrets register. Keeping it separate keeps that surface to the website.

**Different release cadences and different CI.** `inzbc` runs ruff, pytest, coverage, secret
scanning, static analysis and a linked-issue check on every pull request. The site publishes from
the Wix CLI. Merging them means either breaking those checks or weakening them to accommodate a
workflow they were not written for.

The collection engine is separate for the oldest of these reasons: it runs on a schedule against
untrusted sources, so it is kept away from the request-serving application.

---

## Working across all three

Clone them as siblings:

    ~/aisentinels/
      inzbc/
      daily-india-nz-news-agent/
      inzbc-studio-site/

Then start the session with all three visible:

    claude --add-dir ../daily-india-nz-news-agent --add-dir ../inzbc-studio-site

`--add-dir` grants tool access to directories outside the working directory, so one session reads
and edits all three. Without it, an agent rooted in `inzbc` cannot see the other two, and the
failure is silent: it does not report a missing repository, it simply reasons as though the work
does not exist.

A shell alias is worth the thirty seconds:

    alias inzbc='cd ~/aisentinels/inzbc && claude \
      --add-dir ../daily-india-nz-news-agent \
      --add-dir ../inzbc-studio-site'

### What this does not do

**It does not make one commit span repositories.** Git has no such thing. Three repositories means
three commits and three pull requests. What `--add-dir` fixes is *knowing*, not *committing*.

A change that touches two repositories is a change that needs the sequencing thought through:
usually the contract lands in `inzbc` first, then the consumer follows. That is a feature. A single
commit spanning a shared contract and its consumer is how a contract change ships without anyone
reviewing the contract.

---

## The rule that matters most

**Controlled documents live in `inzbc` and nowhere else.** The SIP operating documents, the ADRs,
the decision records and the client answers have exactly one home. The other two repositories link
to them rather than copying them, because a copied controlled document drifts, and a drifted
controlled document is worse than no copy at all.

`daily-india-nz-news-agent` already follows this: its own documentation points back here rather than
restating.

---

## Related

- [`README.md`](README.md) — the documentation index
- [`project-charter.md`](project-charter.md) — the programme, and which module lives where
- [`studio-build-spec.md`](studio-build-spec.md) — what gets built on the Studio site
