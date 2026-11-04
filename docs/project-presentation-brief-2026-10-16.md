# INZBC project: presentation and technical briefing

Prepared 16 October 2026. Read sections 1–4 for the project story, 5–8 for technical questions,
and 9–13 for results, timeline, demonstration and next steps.

This briefing checks the platform against `main` at `1d304ab`, committed code and evaluation
reports, recent GitHub issue/PR status, and the actual live quality-evaluation artifact.
Website and collector context also draws on their local repository checkouts; neither is a
fresh verification of a deployed service. This is a presentation aid, not a new scope approval.

## 1. The project in one minute

> We are developing a digital platform for the India New Zealand Business Council, or INZBC.
> It brings together trade intelligence, sourced FTA guidance, communications drafting and a
> refreshed public website. The main engineering challenge is making information useful while
> keeping evidence, decisions and publication under human control.
>
> Our platform collects potential intelligence, supports assessment, records review and approval,
> and preserves an audit history. The FTA Explainer retrieves approved source material rather
> than generating tariff advice. AI helps with scoring, drafting and advisory quality checks,
> but it cannot grant approval or independently publish an output.
>
> We have built and tested the core application and are improving evaluation, integration and
> operational readiness. Production launch is still gated, and the remaining deployment and
> handover work is clearly recorded.

**Useful opening sentence:** “Our contribution is a governed workflow around information and AI:
every important output needs evidence and a recorded human decision.”

## 2. What problem are we solving?

INZBC needs to turn information about India–New Zealand trade into material that staff and
members can use. The project brief describes fragmented information, separate membership
systems, website improvement needs and a need for clearer control over organisational knowledge.

| Need | Project response | Practical value |
|---|---|---|
| Find relevant developments without treating every headline as urgent | Strategic Intelligence Platform (SIP) | A structured path from candidate information to a reviewed brief |
| Explain opportunities using traceable material | FTA Opportunity Explainer | Source-linked guidance and explicit limits when coverage is missing |
| Draft communications consistently | Communications Assistant | Staff supply a brief; AI drafts; a named human reviews |
| Improve the public information journey | Website rebuild in `inzview` | A clearer public-facing experience, with separate release approval |
| Preserve accountability | Shared identity, roles, decisions and audit records | A record of who acted, what they approved and which report version it concerned |
| Avoid conflicting member records | Retain Member Jungle and link out | One membership system of record rather than a second member database |

These are intended benefits. We have not measured hours saved, member adoption, increased revenue
or organisational return on investment, so those should not be presented as achieved outcomes.

## 3. What is in the project today?

The original programme described nine modules. The four principal build areas are the website,
SIP/trade intelligence, FTA Explainer and Communications Assistant. Wider module specifications
are planning context, not evidence that all nine systems have been delivered.

| Area | What exists | Boundary or remaining work |
|---|---|---|
| SIP | Run lifecycle, candidate handling, source checks, report versions, QA and decision endpoints, UI integration and audit history | A fully agentic tool-use loop is still open; operational acceptance is separate |
| FTA Explainer | Curated corpus, keyword/synonym retrieval, citations, structured tariff fields, no-match handling and missing-product warning | Corpus coverage is limited; API integration of audience depth remains open |
| Communications Assistant | Structured staff brief, draft generation, persisted drafts and named-reviewer approval | Staff-prose privacy risk remains; SSE streaming is unfinished |
| Dashboard | UI and backend summaries over recorded platform data | Wider board metric definition and additional dashboard work remain open |
| Website | Separate `inzview` implementation using Astro/React and Wix tooling | Production cutover and delivered-site accessibility/redirect evidence need verification |
| Membership | Existing link-out UI shell and Member Jungle decision | No new internal member portal/access-control or CRM build is authorized; Zoho deferred |
| Operations | Startup scripts, Docker build, operator material and handover pack | Hosted service, timed restore and recipient walkthrough are not verified complete |

**Status vocabulary:** built means code exists; tested means a stated check ran; deployed means a
service is actually hosted; accepted means the relevant human approval/evidence exists. These
are different milestones.

## 4. How the system works

### The architecture in plain language

There are three repositories with different responsibilities:

- **`inzbc`:** the platform application, shared API, database, staff interfaces and controls.
- **`daily-india-nz-news-agent`:** the separate collection engine that handles external feeds.
- **`inzview`:** the public website. Earlier documents discuss Wix Studio/Velo; the newer
  website implementation uses Astro, React and Wix tooling.

```text
Public sources → collection and candidate processing → platform API → PostgreSQL
                                                        ↑
Staff → unified React application → session/role checks → workflow actions
                                                        ↓
                                  source refusal → redaction → model gateway → provider

Public FTA question → corpus retrieval → cited answer / no match / coverage warning
                                        (no LLM call in this retrieval path)

Membership journey → Member Jungle link-out
```

The public site and staff platform have different trust boundaries. Staff actions use platform
sessions and role checks. The public FTA query endpoint is deliberately anonymous. A proposed
website/platform boundary ADR explains why staff tools should use the platform origin; its
proposal status should not be described as a signed client decision.

### One intelligence run

1. An authorized operator creates and authorizes a run.
2. Candidate information is captured, deduplicated and associated with sources.
3. Assessment recommends relevance and signal strength; human verification remains separate.
4. Selected candidates form a versioned report. A content hash binds the submitted material.
5. A reviewer records QA. A failed review can return the report for correction.
6. The appropriate human records the decision and distribution authority.
7. Delivery is recorded separately; approval does not by itself mean an email was sent.
8. Audit records preserve the actions and evidence references.

This is a simplified explanation, not the full state-machine specification. The application
enforces legal transitions in code and uses database constraints and append-only records for
additional protection. An LLM response cannot substitute for a required human gate.

## 5. Technology choices and why we made them

| Technology | Role | Reason |
|---|---|---|
| Python 3.11+ | Backend and intelligence processing | Reuses the Python collector and keeps one backend language across a small team |
| FastAPI | HTTP API | Explicit operations, validation and an OpenAPI contract |
| Pydantic | Data contracts | Validates incoming requests and rejects malformed model recommendations |
| PostgreSQL with psycopg | Persistent records | Transactions, foreign keys, checks, versioning and append-only audit controls |
| React and TypeScript | Staff application | Typed interfaces, reusable UI and independently testable modules |
| Vite and pnpm | Frontend build/workspace | Builds the module UIs and the unified shell |
| Generated OpenAPI TypeScript | API/client alignment | Makes contract changes visible; CI detects regeneration drift |
| Docker and GitHub Actions | Packaging and verification | Reproducible image build, database-backed CI checks and endpoint smoke tests |
| Astro/React and Wix tooling | Public website | Website implementation remains separate from the governed staff backend |
| External model gateway | Model access | One place for provider configuration, redaction, retries and usage metadata |

The current committed API schema contains **60 operations across 51 paths**. A local corpus
import confirms **23 FTA facts, 22 marked confirmed**. These counts describe this snapshot;
they are not a claim that every path or every fact was manually tested in this briefing.

**Alternatives considered:** ADR-0001 records Go, an all-TypeScript backend and stronger typed
languages among the alternatives. Python was selected for reuse, maintainability and delivery
time. ADR-0004 explains the move from a scheduled process to a persistent service: approval can
wait for a human and must survive the process ending. Earlier hosting proposals were amended
because of cost constraints; they are not evidence of a current deployed service.

## 6. The LLM configuration: what to say when asked

**Short answer:** “The platform gateway defaults to OpenAI `gpt-4.1-mini`, called from the
server through the Responses interface. Configuration is supplied at runtime. The gateway
checks the declared data source, applies the approved redaction policy, makes the request and
records content-free usage metadata. We are integrating an existing model, not training one.”

The table below describes the platform gateway, not a guarantee that the separate collector
uses identical settings. No runtime `.env` file or secret value was read for this briefing.

| Setting | Verified implementation |
|---|---|
| Default provider | `SIP_MODEL_PROVIDER=openai` |
| Default model | `gpt-4.1-mini`; overridden by `SIP_MODEL_NAME` |
| Optional provider | `perplexity`, selected explicitly; requires its own model name and key |
| Provider credentials | `OPENAI_API_KEY` or `PERPLEXITY_API_KEY`; server-side only |
| Interface | OpenAI SDK `client.responses.create(...)` |
| Perplexity endpoint | Fixed `https://api.perplexity.ai/v1`; provider tools explicitly disabled |
| Data-source declaration | Every completion requires `PromptSource`; prohibited origins are refused first |
| Redaction policy | `REDACTION_POLICY_PATH`; committed policy is `config/redaction-policy.json` |
| Missing key or policy | Raises an error; does not fabricate an answer |
| SDK timeout | 30 seconds; this is not a hard total end-to-end request deadline |
| Retry handling | At most two gateway attempts, with a two-second delay; SDK retries disabled |
| Storage request | `store=False`; this is not a promise about every provider retention practice |
| Temperature and `top_p` | Not explicitly sent by this gateway; do not claim a configured value such as 0 |
| Output-token cap | No explicit `max_output_tokens` is sent by the gateway |
| Seed and model snapshot | No explicit seed; the default model name is not a dated snapshot pin |
| Tools and autonomy | No general autonomous tool loop is delivered by this completion gateway |
| Cost rates | Optional operator-supplied input/output USD rates per million tokens |
| Usage records | Provider, model, elapsed time, attempts, result, available token counts and cost basis |
| Durable usage storage | Appended to the audit service when `DATABASE_URL` is configured; otherwise logged locally |

**What these parameters mean:** temperature/top-p affect sampling; token caps constrain response
length; timeouts bound waiting at the client layer; retries trade resilience against latency and
possible extra cost. Our current code explicitly sets some controls and leaves others to the
provider. Choosing sampling settings, output caps or snapshot pinning would be future engineering
work requiring validation, not something this document silently changes.

### Where AI is used

- **Candidate scoring:** recommends NZ, India and member relevance on integer 0–5 scales,
  signal strength, source confidence and a reason. It does not assign factual verification.
- **Communications drafting:** supports newsletter sections, LinkedIn posts, event announcements
  and member spotlights, with formal/warm/concise tone selections. Output remains a draft.
- **Advisory brief-quality judging:** scores NZ relevance, member actionability, evidence support
  and signal discipline. Any dimension below 3 produces `needs_revision` in application code.

The quality judge accepts up to 12,000 characters each for the brief and evidence, demands
strict scores and reasons, and rejects extra or invented approval fields. It advises the reviewer;
it cannot perform QA sign-off, authenticate a source or authorize distribution.

### Where AI is deliberately absent

The current FTA answer retrieval path searches the curated corpus. It does not ask an LLM to
invent an explanation, tariff or source. Embeddings/pgvector and hybrid retrieval are open
engineering ideas, not the current production retrieval mechanism. We have no verified
project-specific model training or fine-tuning result to present.

## 7. Data, privacy, security and human control

| Control | What it does | Important limit |
|---|---|---|
| Server-side credentials | Keeps model keys outside browser code | Runtime account custody and deployment still need operational verification |
| Session auth, CSRF and roles | Protects staff reads/writes and restricts actions by role | Anonymous FTA lookup is intentionally public |
| Separation of duties | Checks recorded participation before verification/approval; exceptions have records | Multiple roles held by one operator require the documented exception process |
| Source refusal | Rejects declared raw member records, CRM notes, board material and private messages | A source declaration is not automatic proof of the text's true origin |
| Redaction | Removes configured formatted identifiers before external model calls | Regex cannot reliably detect names or confidential meaning in prose |
| Strict model-output parsing | Refuses malformed JSON, invalid types and unauthorized fields | Correct structure does not prove factual or semantic correctness |
| Workflow gates | Keeps approval authority in application logic | Prompt instructions alone are not a security boundary |
| Append-only history | Preserves controlled audit/decision records against ordinary update/delete paths | Does not mean the system is immune to every privileged administrator attack |
| Human publication gate | Requires a named human and recorded authority | Reviewing output cannot undo sensitive input already sent to a provider |

The Communications Assistant's structured fields reduce the opportunity to paste large private
documents, but staff can still type sensitive prose. Issue #303 retains a written residual-risk
acceptance condition. Phone approval has been reported; a written record satisfying that
condition has not been supplied. Do not describe this risk as solved.

Member Jungle remains the member system of record. A portal shell does not authorize duplicating
membership records. Production and automated distribution remain disabled pending launch
authority. No confidential acceptance documents, credentials or personal contact data belong in
the presentation.

## 8. What ideas did we develop during the project?

These are project design contributions, not claims of inventions that are globally new.

| Idea or refinement | Why it mattered | Evidence/status |
|---|---|---|
| Give AI advisory roles while code owns authority | A confident model must not approve its own output | Implemented scoring contracts, state machine and human gates |
| Treat source verification separately from relevance/confidence | An interesting article is not automatically verified evidence | Implemented assessment/verification distinction |
| Use append-only decisions bound to report versions | Later approval must refer to the actual material reviewed | Implemented report/decision/audit layers |
| Show missing product coverage explicitly | Generic trade guidance can look like a product-specific answer | Warning and INZBC follow-up delivered in #423; client agreement recorded |
| Prefer named-product relevance over generic framing words | Words such as “exports” could outrank the product a member asked about | Keyword/synonym/framing ranker work and regression evaluation |
| Separate a visible test set from held-out questions | A map tuned against known questions can look misleadingly perfect | Existing main evaluation; separate held-out delivery proposed in open PR #416 |
| Measure alternative rankers before adopting them | BM25 is not automatically better on this domain | Comparison reports exist; no new production ranker approved by comparison alone |
| Make a quality rubric executable | “Good brief” becomes explicit dimensions with bounded scores | Judge and regression pipeline merged in #426; synthetic live result verified |
| Allow an evidenced “no material new signal” outcome | Avoid creating filler merely to produce a daily brief | Explicitly supported in the quality rubric |
| Centralize provider access and content-free cost records | Avoid separate callers forgetting safeguards or logging sensitive prompts | Gateway, provider selection and usage audit implemented |
| Unify module UIs into one application | Operators should not need several dev servers to use the workflow | September platform runner and shell integration |
| Retain Member Jungle instead of rebuilding membership | Reduce duplicate records and unnecessary scope | Confirmed decision recorded 16 October |

**Ideas still requiring delivery:** embeddings/pgvector (#63), the tool-use daily-run
orchestrator (#62), streamed communications output (#65), live scoring calibration (#39),
and runtime API integration of FTA audience depth (#392). These are existing work items, not
new assignments or delivery promises created by this briefing.

## 9. Testing and the results we can defend

### Automated engineering checks

The current CI covers Python lint/tests with a 90% coverage gate, generated API-type drift,
frontend lint/typecheck/tests/build, Storybook compilation, Semgrep, gitleaks, workflow validation,
links, Docker build and HTTP smoke tests. Nine jobs passed on PR #429's final head before merge.

The September v1.0 release records 1,188 Python and 410 frontend tests. Those are historical
release counts, not a fresh pass count from this briefing. Some local Python runs skip
database-dependent tests; those skips must not be described as database coverage.

### FTA retrieval evidence

The committed `current.json` contains 55 questions: 45 answerable and 10 no-match cases.
Recorded hit@1, hit@3, mean reciprocal rank and no-match accuracy are all **1.000 on that set**.

- **Hit@1:** the expected result is ranked first.
- **Hit@3:** an expected result appears in the first three.
- **MRR:** rewards putting the expected result near the top.
- **No-match accuracy:** checks that unanswerable cases remain unmatched.

This is a known development set. It is not proof of 100% real-world accuracy. PR #416 reports
**0.800 hit@1 on ten separate synonym questions**, compared with 0.500 without the synonym map.
That PR is still open; its result was read from the submitted evidence, not independently rerun
for this briefing. Its “visitor numbers” no-match and incorrect “economic impact study” result
show useful remaining weaknesses. Some reported held-out items were already synonym-map keys,
so do not call the entire set perfectly blind. Once questions are examined or used for tuning,
fresh questions are needed for another genuinely unseen evaluation.

### Live LLM quality evidence

The actual artifact from [quality run 38814897919](https://github.com/India-New-Zealand-Business-Council/inzbc/actions/runs/38814897919)
was downloaded and read. It ran on `main` with `gpt-4.1-mini`, using rubric
`sip-quality-v1` and its pinned fingerprint. All eight synthetic cases met the configured
expectations; the report contains `failures: []`.

Examples: supported specific action scored 5/5/4/5; an unsupported tariff claim scored 1/1/0/1;
vague action scored 3/1/3/4. Six cases were flagged for revision; two were not.

This is a real provider result on hand-authored synthetic fixtures. It does not establish
real-article calibration, universal injection resistance, independent human agreement or client
acceptance. Ordinary PR CI runs offline checks; the live quality workflow is manually triggered
and is not a required branch check. No new model call was made for this briefing.

## 10. Timeline: what happened and what remains planned

Dates below are project/repository milestones, not claims that every associated client
acceptance activity happened on that day. July–September events are supported by git history,
ADRs and the changelog. October status is checked against the current decision records and GitHub.

| Period | Main activity | Demonstrable outcome |
|---|---|---|
| 13 July 2026 | Placement began, according to the charter | Start of discovery and planning period |
| 18–22 July | Initial repository, discovery, page specifications, FTA/SIP material and backend decision | Project foundation; Python/FastAPI/Pydantic/Postgres direction |
| 23–31 July | Source handling, initial API/UI contracts, service graduation, persistence and audit design | FTA API/UI slice, stable corpus IDs, database adapter and decision design |
| 27–31 July launch window | Workbook-based controlled-launch process appears in project records | Historical manual phase; not proof of a production run through the new application |
| 1–13 August | UI specifications, redaction enforcement, data-boundary decisions, auth, roles and API expansion | Security and workflow foundations; source refusal and append-only controls |
| 18–30 August | Acceptance plan, draft persistence, facts library, QA/report integration, seed data and additional source work | More complete staff workflow and evidence-backed test/demo data |
| 5–10 September | Database/test corrections, authorization endpoint, end-to-end walk, shared shell and integration fixes | v1.0.0 and v1.1.0 tagged 10 September; fixtures replaced in key run/report flows |
| 5 October onward | Studio 6 planning period | Continued evaluation, integration and evidence preparation |
| 13–14 October | Synonym/framing retrieval improvements and ranker comparisons | Development evaluation improved; limits of the visible question set identified |
| 16 October | Dependency/security patches, usage auditing, scoring regression, product warning, handover pack and quality judge | Merged engineering work, recorded client decisions and successful synthetic live quality run |
| 16 October | Review and contributor policy update (#429) | Weekly review before Monday report submission; continued approved work while review is pending |
| Remaining October–December | Evaluation, integration, acceptance evidence and handover preparation | Planned work; no automatic promise of completion or production launch |

One personal Studio 6 plan records practice PDR in 2–6 November, evidence readiness on
20 November, final PDR in 23–27 November, submission on 27 November at 10:30 AM and handover
in 30 November–4 December. **Confirm these dates against the current course/team schedule
before presenting them as shared deadlines.** Its proposed review rota and ADR-0008 process
changes were not adopted and are not part of this delivery policy.

## 11. Honest current status and remaining gates

| Item | Status as checked 16 October |
|---|---|
| Core platform and quality judge | Implemented and merged; #64 remains open despite the delivered advisory pipeline |
| Production launch | Not authorized; testing and deployment preparation only (#189) |
| Hosted deployment | INZBC-owned account reported ready; no verified Render service/deployment in the current record (#99) |
| Sign-off | Tech lead reports written broad sign-off received; detailed version-specific UAT evidence remains outstanding (#133) |
| Security staff-use condition | Written staff-prose residual-risk acceptance still needed (#303/#40) |
| Forms | Routing, system of record, retention and notice decisions pending (#45) |
| Handover | Pack prepared; walkthrough explicitly not completed (#291) |
| Recovery | Timed restore of an actual platform backup remains unproven |
| Membership | Retain Member Jungle; no new internal portal/CRM build; Zoho deferred |
| Technical integration | #39, #62, #63, #65 and #392 remain open; other UI/evidence tasks are also tracked |

An open issue is not always proof that no related implementation exists. Conversely, a closed
issue or merged PR is not sufficient proof of deployment, client acceptance or operational recovery.

## 12. Suggested presentation and demonstration

### A ten-minute speaking outline

| Time | Explain | Show |
|---|---|---|
| 0–1 min | Client problem and intended value | The one-minute explanation and problem table |
| 1–2 min | Scope and roles | Four principal build areas and the repository boundary |
| 2–4 min | The governed intelligence workflow | Select a seeded run, its candidates and recorded source coverage |
| 4–5 min | Evidence-backed FTA guidance | A supported corpus query and a no-match/coverage-warning case |
| 5–6 min | Where AI helps and where authority stays human | Gateway configuration and draft/reviewer flow |
| 6–7 min | The ideas developed through implementation | Product framing, quality rubric and append-only decisions |
| 7–8 min | Testing and results | Known-set versus separate-set results; live synthetic quality artifact |
| 8–9 min | Timeline and engineering lessons | July–October milestones and one integration bug fixed |
| 9–10 min | Remaining work and handover | Concrete gates; questions |

### Demonstration checklist

Use a prepared local/demo environment with synthetic data. `scripts/platform.ps1` is the
platform runner; `scripts/demo.ps1` is the smaller FTA-only path. Verify the environment before
the presentation rather than assuming the scripts or model account are ready on the day.

1. Select a seeded run and show that the header and candidate list refer to that same run.
2. Show source coverage, report selection and a read-only view of recorded decisions/audit.
3. Demonstrate a refusal or failed gate using a prepared test account/scenario.
4. Ask the FTA Explainer “wool”; show source attribution, then a prepared unsupported query.
5. Show a stored synthetic communications draft and its reviewer requirement. If live model
   access is unavailable, say so and use a clearly labelled saved example.
6. Show the evaluation report; explain one success and one known failure.

Do not use production credentials, real member data, live sending or a public-site cutover as
a presentation demonstration. A recorded delivery in a synthetic walkthrough is not a real send.

## 13. Likely questions and clear answers

**Is this just an AI chatbot?**
The main application is a workflow, data and control system. AI is used at specific steps;
identity, report versions, state transitions and approvals are implemented outside the model.

**Why not let AI publish automatically?**
INZBC needs attributable, source-backed communications. A model can produce a plausible error;
the system therefore keeps consequential release decisions with named humans.

**Is the FTA Explainer RAG?**
It retrieves from a sourced knowledge corpus, but the current public answer path does not perform
LLM generation. Describe it as curated retrieval. Vector/embedding retrieval is future work.

**Why did you choose this model?**
`gpt-4.1-mini` is the implemented default. The gateway allows configuration and we now have a
bounded quality-evaluation mechanism. We have not established that it is the optimal model
through a broad comparative benchmark; model replacement needs evidence.

**Did you train a model? What is the training dataset?**
No project-specific training or fine-tuning is verified. We use existing external models,
project prompts, a curated FTA corpus and synthetic regression/evaluation fixtures. The corpus
and test fixtures are not a model training dataset.

**How do you stop hallucinations?**
We reduce exposure through sourced retrieval, strict contracts, explicit missing-evidence
handling and human review. These do not eliminate every semantic error. The separate FTA
question set already contains an incorrect match, which we report rather than hide.

**Is the model deterministic?**
We do not claim that. The gateway sets no explicit temperature, seed or dated model snapshot.
Strict parsing constrains accepted structure, not repeated semantic identity.

**What happens if the model fails?**
The gateway has bounded retries and surfaces failure. Missing configuration or malformed output
does not become a fabricated recommendation. A failed usage-audit write prevents returning the
result and does not trigger another provider call.

**How much does it cost?**
There is no verified total operating bill in this briefing. The gateway records available token
usage and either provider-reported USD cost or a labelled estimate using configured rates:

`estimated USD = (input tokens × input rate + output tokens × output rate) / 1,000,000`

Missing rates/counts mean unknown cost, not zero. Hosting plans, quotas and model prices must
be checked when deployment is arranged; earlier free-tier assumptions are not current guarantees.

**How does it scale?**
The design separates collection, web requests and persistent state. That is an architectural
starting point, not load-test evidence. We have not demonstrated production concurrency,
availability or a capacity/SLA figure for this briefing.

**What were the hardest engineering problems?**
Preserving approval authority across processes, binding decisions to actual report content,
enforcing separation of duties, connecting UI state to the correct run, and handling sensitive
text before an external call. September fixes included run-ID confusion, wrong-run candidate
selection, incorrect content hashing and clock differences between the app and database.

**What did each teammate contribute?**
The documented lanes are Bhanu: technical lead, backend/control platform and shared contracts;
Roshan: intelligence, source/data and FTA work; Paras: product experience, frontend and website
work. Use PRs and individual worklogs for precise attribution rather than assigning every
cross-cutting feature to one person.

**What is the next step?**
Complete the existing evaluation/integration tasks, prepare and verify the hosted environment,
record outstanding acceptance/security evidence, and complete recipient handover and recovery
verification. Production remains a separate client decision.

## 14. Source map and limits of this briefing

| Topic | Evidence to open |
|---|---|
| Original purpose, scope and start date | [Project charter](project-charter.md), [programme brief](inzbc-ai-operating-system.md) |
| Current relayed decisions | [16 October decision update](meetings/client/2026-10-16-decision-update.md) |
| Handover and missing evidence | [Handover pack](handover-pack.md), [acceptance register](testing/acceptance-register.md) |
| Backend and service decisions | [ADR-0001](decisions/0001-backend-language.md), [ADR-0004](decisions/0004-platform-graduation.md) |
| Platform implementation | [API entry point](../services/api/main.py), [schema](../schemas/openapi.json), [state machine](../schemas/state-machine.md), [database](../database/schema.sql) |
| Model settings | [Gateway code](../services/api/model_gateway.py), [gateway documentation](model-gateway.md) |
| Privacy limits | [Data-boundary code](../services/api/prompt_boundary.py), [ADR-0006](decisions/ADR-0006-model-data-boundary.md) |
| FTA knowledge and measured results | [Corpus](../apps/fta/corpus.py), [current evaluation](../apps/fta/eval/results/current.json), [ranker comparisons](../apps/fta/eval/results/variants.json) |
| Separate question-set proposal | [Open PR #416](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/416) |
| Quality judge and verified live run | [Quality evaluation](quality-evaluation.md), [judge code](../apps/sip/core/quality.py), [successful run and artifact](https://github.com/India-New-Zealand-Business-Council/inzbc/actions/runs/38814897919) |
| Release history and integration lessons | [Changelog](../CHANGELOG.md), repository git history |
| Team responsibilities and provisional dates | [Workstreams](workstreams/README.md), [Bhanu](workstreams/bhanu.md), [Roshan](workstreams/roshan.md), [Paras](workstreams/paras.md), [Studio 6 plan](workstreams/roshan-studio6-plan.md) |
| Weekly review and contribution rules | [CONTRIBUTING](../CONTRIBUTING.md), [merged policy PR #429](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/429) |

Older README, architecture diagrams, charters and personal plans contain historical status that
has since changed. This briefing uses later merged code, the dated decision update and current
issue/PR status where they conflict. Reported sign-off is attributed; unavailable evidence is
not reconstructed. This preparation did not rerun the full test suite, audit every source fact,
perform a deployment, verify the live website, run client UAT or authorize additional scope.
