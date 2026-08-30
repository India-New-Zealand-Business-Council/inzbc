# INZBC platform architecture

System diagrams for the INZBC AI Operating System. Diagrams are Mermaid so they version with the
code and render on GitHub. Update them in the same pull request as the change they describe.

Status is marked on every component: **built** (merged, tested), **contract** (specified, not yet
implemented) or **planned** (decided, not started). Nothing here is aspirational — if it says built,
there is code and tests behind it.

---

## 1. System context

Who and what the platform talks to.

```mermaid
graph TB
    subgraph people[People]
        CEO["CEO / SIP Owner<br/>authority + decisions"]
        ANALYST["Analyst<br/>runs the daily SOP"]
        REVIEWER["Quality Reviewer<br/>SIP-188 QA"]
        MEMBER["INZBC member<br/>FTA questions"]
    end

    subgraph platform[INZBC platform]
        SIP["SIP<br/>trade intelligence pipeline"]
        FTA["FTA Opportunity Explainer"]
        SITE["Public website content"]
    end

    subgraph external[External services]
        AGENT["daily-india-nz-news-agent<br/>collection engine, separate repo"]
        MODEL["Model provider<br/>OpenAI"]
        SOURCES["112 mandatory sources<br/>SIP-185 register"]
    end

    ANALYST --> SIP
    REVIEWER --> SIP
    CEO --> SIP
    MEMBER --> FTA
    AGENT --> SIP
    SOURCES --> AGENT
    SIP --> MODEL
    FTA -.->|no model call| MODEL
    SIP --> CEO
```

The FTA Explainer deliberately makes **no model call** — it answers only from a sourced corpus, so
it cannot hallucinate a trade fact.

---

## 2. SIP pipeline components

```mermaid
graph LR
    subgraph collect["apps/sip/collector — built"]
        MAP["mapping.py<br/>article to Candidate"]
        ING["ingest.py<br/>batch write, per-item isolation"]
        DED["dedupe.py<br/>cross-run duplicates"]
        SRC["source_register.py<br/>112 mandatory, fail-closed gate"]
        ASSESS["assessment.py<br/>validated PATCH path"]
        VER["verification.py<br/>High/Critical gate"]
    end

    subgraph core["apps/sip/core — built"]
        SCORE["scoring.py<br/>SIP-050 relevance/signal/confidence"]
        ORCH["orchestrator.py<br/>run state machine + human gates"]
    end

    subgraph svc["services/api — built"]
        GW["model_gateway.py<br/>single server-side model path"]
    end

    subgraph data["Persistence"]
        DB[("Postgres<br/>database/schema.sql — contract")]
        API["REST API<br/>schemas/api-contract.md — contract"]
    end

    MAP --> ING
    DED --> ING
    ING --> API
    SRC --> API
    ASSESS --> VER
    ASSESS --> API
    SCORE --> GW
    SCORE --> ASSESS
    ORCH --> SCORE
    ORCH --> SRC
    ORCH --> VER
    API --> DB
```

---

## 3. Run state machine

The SIP-184 daily run. Run state is mutated in exactly one place: `RunRepository.apply_transition`
(`services/api/persistence.py`), which issues the compare-and-swap
`update runs set state = ..., version = version + 1 where id = ... and version = ...`.

That is not a bypass of the state machine. `persistence.py` imports `is_legal_transition` and
`is_human_gated` from `apps/sip/core/orchestrator.py` and refuses an illegal jump, or a gated
transition with no approval, before it writes. `Orchestrator.advance()` enforces the same table
in memory and is exercised by the tests and by audit-log replay; it has no production callers
today, so it is the second implementation of the rule rather than the path that applies it.

Transitions labelled **(human)** below require a decision recorded in `decision_records`, named by
`approval_ref`. An agent can never cross them alone.

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> RunAuthorised: authority + version check (human)
    RunAuthorised --> CoverageLocked: fix exact 24h window
    CoverageLocked --> Scanning
    Scanning --> CandidateReview
    CandidateReview --> ReportDrafted
    ReportDrafted --> QAInProgress
    QAInProgress --> AwaitingCEODecision: QA pass (human)
    QAInProgress --> QAFailed: Critical failure (human)
    QAFailed --> ReportDrafted: correction + re-review (human)
    AwaitingCEODecision --> ApprovedForManualDistribution: CEO decision (human)
    AwaitingCEODecision --> Continue: (human)
    AwaitingCEODecision --> ContinueWithCorrection: (human)
    AwaitingCEODecision --> Paused: (human)
    AwaitingCEODecision --> Stopped: (human)
    ApprovedForManualDistribution --> Distributed: manual send recorded (human)
    Distributed --> Closed
    Paused --> CoverageLocked: resumption approval (human)
    Stopped --> [*]
    Closed --> [*]
```

`Stopped` is terminal for that run id — a stopped run is never resumed under the same id.

---

## 4. Fail-closed controls

Where the platform refuses rather than guesses. Each is enforced in code and covered by tests.

Two different mechanisms appear below, and the distinction matters. Most of these **raise** and so
refuse the operation outright. The mandatory-source check is a **reporting** control:
`missing_mandatory_outcomes()` returns the list of uncovered source ids and raises nothing. It is the
QA step (SIP-188) that must treat a non-empty list as a Critical stop. The code surfaces the gap; the
gate is procedural.

```mermaid
flowchart TD
    A["Mandatory source has no recorded outcome"] -->|"missing_mandatory_outcomes() returns ids"| STOP1["Non-empty list = Critical stop at QA<br/>(reported, not raised)"]
    A2["Source id cannot be resolved to a db id"] -->|SourceIdUnresolved| STOP7["Source check refused<br/>source_checks.source_id is NOT NULL"]
    B["Model returns malformed or out-of-range output"] -->|ScoringParseError| STOP2["Candidate stays unscored<br/>no assumed values"]
    C["High/Critical signal without verification"] -->|UnverifiedHighSignalError| STOP3["Assessment refused"]
    D["Gated transition without a human decision"] -->|HumanGateRequired| STOP4["State unchanged"]
    E["FTA fact not confirmed against a Tier 1 source"] -->|confirmed filter| STOP5["Suppressed, escalate to INZBC"]
    F["No model API key configured"] -->|GatewayNotConfiguredError| STOP6["No fabricated response"]
```

---

## 5. Scoring and verification sequence

The path a candidate takes from capture to an applied assessment.

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant S as scoring.py
    participant G as model_gateway.py
    participant M as Model provider
    participant V as verification.py
    participant API as SIP API

    O->>S: score_candidate(headline, source, summary)
    S->>G: complete(prompt)
    G->>M: responses.create (retry once)
    M-->>G: text
    G-->>S: GatewayResult
    S->>S: strict JSON parse, reject duplicate keys
    S->>S: validate 0..5 bounds, strict types
    alt output does not match contract
        S-->>O: ScoringParseError (candidate stays unscored)
    else valid
        S-->>O: ScoringRecommendation
        O->>V: enforce_verification_gate(signal, verification)
        alt High/Critical and not verified
            V-->>O: UnverifiedHighSignalError
        else allowed
            O->>API: PATCH candidate (analyst applies)
        end
    end
```

`to_assessment()` never sets `verification` — verification is evidence-driven and human-owned, so the
fail-closed gate stays in charge of High and Critical.

---

## 6. Data model

Entity relationships from `database/schema.sql` (contract stage — not yet migrated).

```mermaid
erDiagram
    roles ||--o{ users : "has"
    users ||--o{ runs : "initiates"
    users |o--o{ runs : "analyst for"
    users |o--o{ runs : "reviewer for"
    users |o--o{ action_register : "owns"
    users |o--o{ exceptions : "owns"
    users |o--o{ user_roles : "holds"
    users |o--o{ decision_records : "decides"
    users |o--o{ audit_log : "acts"
    runs ||--o{ source_checks : "records"
    runs ||--o{ candidates : "captures"
    runs ||--o{ daily_intelligence : "produces"
    runs |o--o{ exceptions : "raises"
    runs ||--o{ report_versions : "produces"
    report_versions ||--o{ decision_streams : "decided through"
    decision_streams ||--o{ decision_records : "records"
    decision_records |o--o{ decision_records : "supersedes"
    decision_records |o--o{ distribution_deliveries : "authorises"
    source_library ||--o{ source_checks : "checked in"
    source_library |o--o{ candidates : "sourced from"
    candidates |o--o{ candidates : "duplicate_of"
    candidates |o--o{ daily_intelligence : "promoted to"
    watch_lists {
        uuid id PK
        text watch_code UK
        text title
        text status
        date next_review
    }
    action_register {
        uuid id PK
        text action_code UK
        text title
        uuid owner_id FK
        text status
        date due_date
    }
    exceptions {
        uuid id PK
        uuid run_id FK
        text exception_type
        text severity
        uuid owner_id FK
        boolean original_preserved
    }

    roles {
        smallint id PK
        text name
    }
    users {
        uuid id PK
        text email UK
        boolean mfa_enabled
    }
    user_roles {
        uuid user_id FK
        smallint role_id FK
        boolean enabled
    }
    runs {
        uuid id PK
        text run_number UK
        timestamptz coverage_start_utc
        timestamptz coverage_end_utc
        run_state state
        text prompt_version
        boolean production_enabled
        uuid analyst_id FK
        uuid reviewer_id FK
    }
    source_library {
        uuid id PK
        text sip185_code UK
        text name
        smallint layer
        boolean mandatory
    }
    source_checks {
        uuid id PK
        uuid run_id FK
        uuid source_id FK
        source_outcome outcome
        boolean fallback_used
    }
    candidates {
        uuid id PK
        uuid run_id FK
        uuid source_id FK
        text headline
        smallint nz_relevance
        signal_strength signal
        verification_state verification
        uuid duplicate_of FK
    }
    daily_intelligence {
        uuid id PK
        uuid run_id FK
        uuid candidate_id FK
        approval_state approval
    }
    report_versions {
        uuid id PK
        uuid run_id FK
        integer version_number
        text content_sha256
        timestamptz submitted_at
    }
    decision_streams {
        uuid id PK
        uuid report_version_id FK
        decision_kind kind
        uuid current_record_id FK
        integer head_revision
    }
    decision_records {
        uuid id PK
        uuid stream_id FK
        decision_kind kind
        decision_value value
        uuid actor_id FK
        smallint actor_role_id FK
        timestamptz decided_at
        uuid supersedes_id FK
    }
    distribution_deliveries {
        uuid id PK
        uuid authority_record_id FK
        uuid sender_id FK
        text recipient_address
        timestamptz sent_at
    }
    audit_log {
        bigserial id PK
        uuid user_id FK
        text action
        text old_value
        text new_value
    }
```

Two constraints the diagram cannot show, both enforced in the schema:
- `runs` has a check that `analyst_id <> reviewer_id` — nobody reviews their own run.
- `source_checks` has `unique (run_id, source_id)` — one outcome per source per run.

---

## 7. Repository layout

```mermaid
graph TD
    ROOT["India-New-Zealand-Business-Council"]
    ROOT --> INZBC["inzbc — monorepo"]
    ROOT --> AGENT2["daily-india-nz-news-agent — collection engine"]

    INZBC --> APPS["apps/ — site, sip, fta, comms"]
    INZBC --> SERVICES["services/api — model gateway"]
    INZBC --> SCHEMAS["schemas/ — API contract, state machine"]
    INZBC --> DBDIR["database/ — schema"]
    INZBC --> DOCS["docs/ — specs, ADRs, SIP controlled docs"]

    AGENT2 --> AGENTPY["agent.py — fetch, score, digest"]
    AGENT2 --> WF[".github/workflows — manual trigger only"]
```

The collection engine stays a separate repository: it has its own release cadence and runs the live
daily digest, while `inzbc` holds the platform and the controlled documentation.

---

## 8. Service flow diagrams (#331)

Two service flows, both encoding a refusal that is the whole point of the service. Neither
refusal was visible anywhere in the documentation before this section.

> **Note on source doc.** #331 points to `docs/architecture-diagram-plan.md` for "standard and
> full diagram set" — that file does not exist anywhere in this repository's history. This
> section instead extends this file, per #331's own "new file, or extend the SIP file — your
> call, note which in the PR" instruction, matching the Mermaid/status-tag convention the rest
> of this file already uses.

### 8.1 FTA query flow

`answer_query()` from request to response — `apps/fta/explainer.py` (built) called from
`GET /api/fta/query` — `services/api/main.py` (built).

```mermaid
sequenceDiagram
    participant M as Member
    participant API as GET /api/fta/query<br/>services/api/main.py — built
    participant Q as answer_query()<br/>apps/fta/explainer.py — built
    participant C as CORPUS<br/>apps/fta/corpus.py — built

    M->>API: GET ?q="wool tariff"
    API->>Q: answer_query(q)
    Q->>Q: _keywords(q) — strip stopwords/jurisdiction terms
    alt no keywords (blank or stopwords only)
        Q-->>API: []
    else has keywords
        Q->>C: rank against CORPUS by weighted keyword relevance
        Note over Q,C: confirmed filter: entries where confirmed=False<br/>(e.g. unconfirmed ~70% tariff-line figure)<br/>never reach this comparison
        alt no confirmed entry shares a keyword
            Q-->>API: []
        else at least one match
            Q-->>API: list[ExplainerAnswer], ranked
        end
    end
    alt answers == []
        API->>API: no_match(q) — builds NoMatch (#187: no evidence fields)
        API-->>M: HTTP 200, status:"no_match", action_required escalation
    else answers present
        API-->>M: HTTP 200, status:"matched", answers[]
    end
```

**No model call anywhere in this path.** `answer_query()` matches against a curated, pre-sourced
corpus and returns an escalation when nothing confirmed matches — it cannot hallucinate a trade
fact because it contains no code path that generates text. That is a structural property of the
module, not a prompt instruction that could be bypassed.

**Why a no-match is HTTP 200, not 404.** `services/api/main.py`'s `fta_query()` docstring states
it directly: a 404 would push callers toward an error branch that discards the guidance. A
no-match here is a legitimate outcome with its own payload (the Action Required escalation
path), not a failure of the request — so it gets a success status with a status field, the same
way `NoMatch` (built, `apps/fta/explainer.py`) is a distinct type from `ExplainerAnswer` rather
than an exception.

**What this diagram does not cover:** the `answer_query_at_depth()` public/member/internal split
(#187, in review as of this diagram) — `/api/fta/query` still calls the single-audience
`answer_query()` shown above; ranking internals (weighted keyword scoring, tie-breaking) — see
`apps/fta/explainer.py`'s own docstrings; and the FTA UI's rendering of the response, which is
Paras's lane.

### 8.2 Comms draft-to-approve flow

The draft path through `apps/comms/draft.py` (built) and its persistence/approval layer in
`services/api/comms.py` / `services/api/comms_persistence.py` (built).

```mermaid
sequenceDiagram
    participant S as Staff member
    participant API as POST /api/comms/draft<br/>services/api/comms.py — built
    participant D as generate_draft()<br/>apps/comms/draft.py — built
    participant GW as ModelGateway.complete()<br/>services/api/model_gateway.py — built
    participant Repo as CommsDraftRepository<br/>services/api/comms_persistence.py — built
    participant R as Reviewer

    S->>API: {content_type, brief}
    API->>D: generate_draft(gateway, content_type, brief)
    D->>D: build_prompt() — generic, no invented voice/statistics
    D->>GW: complete(prompt, source=STAFF_AUTHORED)
    Note over GW: prompt boundary + redaction — see §9 for the full<br/>layer sequence inside this one call
    GW-->>D: GatewayResult
    D-->>API: draft text
    API->>Repo: create(draft, authored_by=staff.id)
    Repo-->>API: CommsDraftRecord, status="draft"
    API-->>S: {draft, id, status}

    Note over S,R: Nothing sends or publishes here — apps/comms/draft.py's own<br/>docstring: there is no publish path anywhere in this codebase yet

    R->>API: POST /drafts/{id}/approve
    API->>Repo: approve(draft_id, principal=reviewer, reason)
    alt reviewer.id == record.authored_by (BR8)
        Repo-->>API: SelfApprovalError
        API-->>R: HTTP 403 — refused, not an error to work around
        Note over R: A normal outcome, not a failure case. INZBC is one person<br/>holding every role today, so this will be common.
    else different person
        Repo->>Repo: refuse_self_review() passes, record audited
        Repo-->>API: CommsDraftRecord, status="approved"
        API-->>R: {status:"approved", approved_by, approved_at}
    end
```

**The self-approval refusal (BR8, `services/api/comms_persistence.py`) is drawn as a normal
branch, not an error path**, because it is expected to fire routinely: INZBC currently has one
person capable of holding every role, so an attempted self-approval is an everyday occurrence
the flow must handle gracefully, not an edge case.

**What this diagram does not cover:** the redaction/prompt-boundary internals inside
`ModelGateway.complete()` — see §9; the streaming SSE variant (#65, unbuilt); the review UI
(#60, Paras's lane) that would actually present this to a reviewer; and what happens after
`status="approved"` — there is no send/publish step in this codebase, by design, so the flow
ends at approval.

## 9. Model data boundary — defence-in-depth (#332)

Every layer untrusted text passes through before it can reach an external model. ADR-0006's
own reasoning: rule-based redaction structurally cannot catch a name, title or employer written
in prose, so the primary control moved to refusing the *source* rather than trying to clean the
*text*. Reconstructing that argument today means reading four files; this section is that
reconstruction.

```mermaid
flowchart TD
    A["Caller assembles a prompt"] --> B{"Layer 1: Source refusal<br/>services/api/prompt_boundary.py — built<br/>check_source(PromptSource)"}
    B -->|"MEMBER_RECORD, CRM_NOTE,<br/>BOARD_MATERIAL, PRIVATE_MESSAGE"| REFUSE1["ProhibitedInputError<br/>no policy read, no key looked up, nothing sent"]
    B -->|"PUBLIC_SOURCE, STAFF_AUTHORED,<br/>MINIMISED_RECORD"| C{"Layer 2: minimise() field allowlist<br/>services/api/prompt_boundary.py — built<br/>(only for MINIMISED_RECORD callers)"}
    C -->|"non-scalar field, or empty allowlist"| REFUSE2["ProhibitedInputError<br/>a field nobody named cannot reach the prompt"]
    C -->|"scalar fields only"| D{"Layer 3: Policy-driven redaction<br/>services/api/redaction.py — built<br/>config/redaction-policy.json — built, approved 9 Aug 2026"}
    D -->|"REDACTION_POLICY_PATH unset<br/>or file missing"| REFUSE3["RedactionNotConfiguredError<br/>fail closed — absence blocks the send,<br/>never silently permits it"]
    D -->|"policy loaded"| E["Regex rules redact formatted<br/>identifiers (email, phone, tax/company<br/>numbers, cards) against the ORIGINAL text"]
    E --> F{"Layer 4: Gateway<br/>services/api/model_gateway.py — built<br/>ModelGateway.complete()"}
    F -->|"OPENAI_API_KEY unset"| REFUSE4["GatewayNotConfiguredError<br/>never fabricates a response"]
    F -->|"configured"| G["Provider call, one retry on<br/>transient failure"]
    G --> H["Layer 5: Operator procedure<br/>docs/operator-guide.md — planned/procedural<br/>'Do not paste member details into a brief<br/>and rely on redaction'"]
```

**What each layer cannot do, not only what it catches** (a layer documented only by its
successes reads as a guarantee, which is the failure mode ADR-0006 exists to prevent):

- **Layer 1 (source refusal)** cannot verify a caller's declaration — `PromptSource` is *stated*,
  not checked against the actual data. A caller that mislabels `MEMBER_RECORD` text as
  `STAFF_AUTHORED` is not caught here. What it does guarantee: a new call site cannot omit the
  question, since `complete()` has no default source.
- **Layer 2 (`minimise()`)** cannot inspect what is *inside* a permitted scalar field — a `str`
  holding serialised JSON with a name embedded in it passes, because the caller allowlisted that
  field. **Known gap, stated rather than hidden: no module builds prompts through `minimise()`
  yet** — no caller assembles from raw member records today, so this is the rule the first one
  must follow, not a control currently running.
- **Layer 3 (redaction)** cannot catch a name, job title, or employer in ordinary prose — only
  formatted identifiers (regex-matchable emails, phone numbers, tax/company numbers, cards).
  `Delegation lead: Priya Sharma, Chief Executive, Koru Exports Ltd` passes through this layer
  untouched, stated explicitly in `config/redaction-policy.json`'s own approval comment.
- **Layer 4 (gateway)** cannot un-send a payload once a provider call succeeds — retries only
  cover transient failures, not policy correctness.
- **Layer 5 (operator procedure)** is the only layer that can catch what layers 1-4 structurally
  cannot: prose containing a name. It works only if followed — it is instruction, not code, and
  is marked `planned/procedural` rather than `built` for that reason.

**Fail-closed points**, marked explicitly because this is the property the whole design rests
on: a missing `REDACTION_POLICY_PATH` is a refusal (`RedactionNotConfiguredError`), never
permission to send unredacted text; a missing `OPENAI_API_KEY` is a refusal
(`GatewayNotConfiguredError`), never a fabricated response; an empty `minimise()` allowlist is a
refusal, never "send everything." Every one of these defaults to blocking, not to disclosure.

**What this diagram does not cover:** the audit-log write for a completed call (out of this
module, in `services/api/audit.py`); how a caller decides *which* `PromptSource` applies to its
data — that judgement call lives with the caller, this layer only enforces the declared answer;
and the redaction policy's own rule content (see `config/redaction-policy.json` directly for the
current rule set).

## Related documents
- `schemas/api-contract.md` — endpoint contract
- `schemas/state-machine.md` — the authoritative transition list this encodes
- `database/schema.sql` — data model source
- `docs/decisions/` — architecture decision records
- `docs/sip/launch/` — the controlled SIP operating documents
