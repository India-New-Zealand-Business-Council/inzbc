# Architecture diagram plan — coordinator pack

Status: proposed, 20 August 2026. Owner: Bhanu. Delivery: Roshan and Paras (highest priority).

## Why this exists

The project coordinator needs one organised view of everything built. Today the platform has
**seven diagrams, all in one file** (`docs/architecture.md`), and they cover the SIP pipeline well
and everything else not at all.

The specific gap, in C4 terms: the repository has a Level 1 context diagram (§1) and one Level 3
component diagram (§2, the SIP pipeline). It has **no Level 2 container diagram**. Level 2 is the
team view — the one that shows the five user interfaces, the API and the database on a single
page. Current C4 guidance is that Levels 1 and 2 are the two you always create and maintain; Level
3 is selective, and Level 4 only if a tool generates it. We have inverted that.

The result is that nobody can currently see the whole system on one page, and the five UI
applications that exist do not appear in any diagram.

## What is already true (verified 20 August 2026)

| Claim | Reality |
|---|---|
| Diagrams in the repo | 7, all in `docs/architecture.md` |
| API routes implemented | 34, across 12 routers |
| Tables in `database/schema.sql` | 25 |
| UI applications with source | 5 (FTA, SIP, comms, member, dashboard) |
| CI jobs | 9 |
| ADRs | 7 |
| Test suite | 1021 passing, 0 skipped |

Three status tags in `docs/architecture.md` are now stale and contradict the file's own rule that
"if it says built, there is code and tests behind it":

- line 76 — Postgres marked `contract`; the schema is applied and 1021 tests run against it
- line 77 — REST API marked `contract`; 34 routes are implemented and tested
- line 193 — "contract stage — not yet migrated"; the *not migrated* half is still true (#44 is
  open, there is no migration mechanism), the *contract stage* half is not

Fixing these is Bhanu's, not Roshan's or Paras's — they are platform-lane lines.

## The target set

Seventeen diagrams, organised by C4 level then by concern. Seven exist; ten are gaps.

### Level 1 — Context
| # | Diagram | State | Owner |
|---|---|---|---|
| 1 | System context | exists, refresh | Bhanu |

### Level 2 — Containers (the coordinator view)
| # | Diagram | State | Owner |
|---|---|---|---|
| 2 | **Container diagram — 5 UIs, API, database, external services** | **GAP** | Paras |
| 3 | **UI-to-API integration patterns** | **GAP** | Paras |

### Level 3 — Components
| # | Diagram | State | Owner |
|---|---|---|---|
| 4 | SIP pipeline components | exists | Roshan |
| 5 | **API router structure — 12 routers + cross-cutting** | **GAP** | Bhanu |
| 6 | Repository layout | exists, refresh | Bhanu |

### Behaviour and flow
| # | Diagram | State | Owner |
|---|---|---|---|
| 7 | Run state machine | exists | Bhanu |
| 8 | Scoring and verification sequence | exists | Roshan |
| 9 | **Request security spine — session → CSRF → role → SoD → audit** | **GAP** | Bhanu |
| 10 | **FTA query flow, showing the no-model-call boundary** | **GAP** | Roshan |
| 11 | **Comms draft → approve flow, with BR8 self-approval refusal** | **GAP** | Roshan |
| 12 | **SIP UI screen flow mapped to run states** | **GAP** | Paras |

### Data
| # | Diagram | State | Owner |
|---|---|---|---|
| 13 | Entity relationship model | exists, fix status | Bhanu |
| 14 | **Append-only enforcement — triggers, TRUNCATE guards, role grant** | **GAP** | Bhanu |

### Cross-cutting
| # | Diagram | State | Owner |
|---|---|---|---|
| 15 | Fail-closed controls | exists | Bhanu |
| 16 | **Model data boundary — defence in depth layers** | **GAP** | Roshan |
| 17 | **CI/CD pipeline — the 9 jobs and what each gates** | **GAP** | Bhanu |
| 18 | **Environments and deployment topology** | **GAP** | Bhanu |
| 19 | **ADR dependency graph — supersedes, blocks, unblocks** | **GAP** | Bhanu |

## Why ownership is split this way

Each diagram is assigned to whoever owns the code it describes. This is not an administrative
preference — a diagram drawn by someone outside the lane is a guess, and a guessed diagram is worse
than no diagram because it presents as evidence.

`docs/workstreams/` already defines the lanes:

- **Roshan** — `apps/fta/**`, `apps/comms/**` (service side), `apps/sip/pipeline/**`,
  `apps/sip/collector/**`
- **Paras** — `apps/site/**`, `apps/sip/ui/**`, `apps/comms/ui/**`, `apps/fta/ui/**`, and the
  dashboard and member UIs
- **Bhanu** — `services/api/**`, `database/**`, `schemas/**`, security and CI

So Paras owns the container and UI-integration diagrams because he owns all five interfaces, and
Roshan owns the FTA, comms-service and model-boundary flows because he owns those services. The
platform, security, data and CI diagrams stay with Bhanu for the same reason.

## Standard every diagram must follow

Non-negotiable, so the pack reads as one document rather than seventeen personal styles:

1. **Mermaid inside markdown.** It versions with the code and renders natively on GitHub. No
   image files, no external diagramming tools, no screenshots of diagrams.
2. **Status on every component** — `built`, `contract` or `planned`, matching the existing
   convention in `docs/architecture.md`. The rule stands: if it says built, there is code and a
   test behind it.
3. **Every diagram names its source files.** A reader must be able to go from a box to the file
   that implements it.
4. **Prose above and below.** A diagram with no explanation is decoration. State what it shows,
   then state what it does not show.
5. **No aspirational boxes.** If something is designed but not built, it is tagged, not omitted
   and not quietly drawn as though it works.
6. **Update in the same PR as the change.** Already the rule at the top of `docs/architecture.md`.
7. **Make the backend's weight visible.** Assessment feedback was that the project reads as an AI
   API wrapper. That is measurably false — 3.2% of source touches a model and exactly one file
   imports an AI SDK — but the diagrams currently do not show it. Annotate `services/api` and
   Postgres with what they actually contain (routes, routers, tables, constraints, triggers,
   indexes), draw the model provider proportionally as one edge from one module rather than a
   central component, and keep the dashed no-model-call edge on the FTA path prominent. Counts
   come from [backend-engineering-evidence.md](./backend-engineering-evidence.md), never retyped.

## File structure

Split `docs/architecture.md` into `docs/architecture/` with one file per concern, and keep
`docs/architecture.md` as the index that links them.

Reason: three people editing seventeen diagrams in a single 900-line file will conflict on every
pull request. Splitting is what makes parallel delivery possible. The repo convention that a
controlled document lives in exactly one place is preserved — the index is that one place.

```
docs/architecture.md              index + Level 1 context
docs/architecture/containers.md   Level 2 — the coordinator view
docs/architecture/sip.md          pipeline components, run states, scoring
docs/architecture/security.md     request spine, fail-closed, model boundary
docs/architecture/data.md         ER model, append-only enforcement
docs/architecture/delivery.md     CI/CD, environments, ADR graph
```

## Assigned work

Raised 20 August 2026 and placed at the top of each worklog's **Next up**, which is the repo's
actual priority mechanism — a labelled issue alone does not make something top priority here,
position in the ordered backlog does.

| Issue | Owner | Covers |
|---|---|---|
| [#329](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/329) | Paras | Container diagram — diagram 2. **Blocking; do first and alone** |
| [#330](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/330) | Paras | UI integration patterns + SIP screen flow — diagrams 3 and 12 |
| [#331](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/331) | Roshan | FTA query flow + Comms draft-to-approve — diagrams 10 and 11 |
| [#332](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/332) | Roshan | Model data boundary — diagram 16 |

Still unassigned, all in Bhanu's lane and not delegable without turning them into guesses:
diagrams 5, 9, 14, 17, 18 and 19, plus the three stale status-tag corrections above.

## Sequence

Diagram 2, the container view, comes first and alone. It is the one the coordinator most needs, it
is the frame every other diagram hangs off, and it settles the naming that the rest must match.
Nothing else starts until it is merged.

After that the two lanes run in parallel — Roshan on service flows, Paras on UI, Bhanu on platform
— because they touch different files.

## Definition of done

A diagram is done when all of the following are true. This is deliberately stricter than "the
diagram exists", because the coordinator will read these as claims about the system.

- It renders on GitHub. Check the rendered view, not the source.
- Every component carries a status tag.
- Every box traces to a named file that exists.
- The prose states what the diagram does not cover.
- No component is drawn as built unless there is a test behind it.
- The index in `docs/architecture.md` links it.

## Out of scope

- C4 Level 4 (code-level) diagrams. Current guidance is to skip these unless generated
  automatically, and nothing here generates them.
- Rebuilding the seven existing diagrams. Three need status corrections; the rest are sound and
  should be moved, not rewritten.
- Any diagram of modules 2 through 5 (member portal, CRM, sponsors, events). They are unbuilt.
  Drawing them would break rule 5.

## Sources

- [C4 model — levels and 2026 practice](https://visual-c4.com/blog/4-cluster-understanding-c4-model-levels)
- [Practical C4 modelling tips](https://revision.app/blog/practical-c4-modeling-tips)
- [C4 component diagram best practices](https://visual-c4.com/blog/c4-component-diagram-best-practices)
