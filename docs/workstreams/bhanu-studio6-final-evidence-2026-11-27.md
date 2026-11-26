# Studio 6 Final Evidence Addendum — Bhanu Gupta (1000124562)

**Course:** IA728001 / IA732001 Studio 6, Study Block 4, 2026 (5 Oct – 4 Dec 2026)  
**Author:** Bhanu Gupta (Tech Lead — Foundation, Security, Integration & AI Agent Safety)  
**Lecturers:** Dr. Senaka Amarakeerthi, Udara Samarathunga  
**Date:** 27 November 2026  

This document closes every feedback item from the Studio 6 Mid-PDR Feedback Report (`1000124562`, Block 4 2026) and links committed repository artefacts across Objectives `1.1`, `1.2`, `2.1`, `2.2`, `3.1`, and `3.2`.

---

## 1. Mid-PDR Feedback Response Matrix

| Objective | Mid-PDR Feedback Summary | Action Taken & Repository Evidence |
|---|---|---|
| **1.1** | ADR-0010 is strong; evaluate **scalability and maintainability** more explicitly. | Added quantitative scalability, horizontal API scaling, write-throughput, key-rotation maintainability, and operational overhead comparison across Options A–D (Section 2 below; cross-referenced to `docs/decisions/ADR-0010-signed-human-decisions.md`). |
| **1.2** | Broad FTA/SIP process explanation; add **critical evaluation of what worked, limits, and how collected info improved user outcomes**, backed by specific test evidence. | Documented before/after test evidence (`1,792` Postgres CI tests at `94.64%` coverage, `481/481` UI tests, live NewsAPI + `gpt-4.1-mini` E2E verification, PR `#583` live assistant bug fix, and `sponsors_persistence.py` audit-contract fix) plus explicit limitations (self-authored attack suite, rubric-author QA check vs. independent external QA, INZBC-owned production launch `#55`/`#99`/`#133`). |
| **2.1** | Hallucinations named as a risk; strengthen by explaining **causes and effects of hallucinations**, linking to **credible academic/industry APA 7 sources**, and **evaluating how retrieval, citation, and human-approval controls reduce risk**. | Added Section 3 below grounding hallucination mechanisms and operational impacts in Ji et al. (2023), Huang et al. (2025), Lewis et al. (2020), Gao et al. (2023), Kalai & Vempala (2024), NIST AI RMF (2023), and OWASP LLM Top 10 (2025), and mapping each mechanism to our deterministic controls and residual risks. |
| **2.2** | Clearly identify **which GitHub project, PR, or research finding supported each decision** and explain the **specific value added**. | Added full Research-to-Code Traceability Matrix (Section 4) mapping each literature finding to its exact repository, PR (`#62`–`#65`, `#448`, `#449`, `#456`, `#553`, `#572`, `#582`, `#583`, `#584`), measured metric change, and concrete INZBC stakeholder value. |
| **3.1** | Provide a **detailed W1–W8 team activity plan with deadlines/milestones**, **weekly progress/timesheet records**, **formal meeting minutes with actions/owners/dates**, and **updated GitHub board extracts**. | Added Section 5 (W1–W8 Team Activity Plan, weekly hours/progress log, formal dated meeting minutes with action owners and due dates, and plan-change log). |
| **3.2** | Provide concrete **peer mentoring / knowledge-sharing records** (explaining issues and confirming peer learning, not just fixing silently) and **conflict resolution records**. | Added Section 6 documenting structured mentoring interactions (Roshan `#394`/`#446`/`#526`–`#539`; Paras `#553`, `#558`/`#559`, `19090d6`) and three resolved technical/process conflicts (`#320`/`#405`, `#533` vs `#537`, `#551`/`#552`). |

---

## 2. Objective 1.1 Addendum — ADR-0010 Scalability & Maintainability Evaluation

ADR-0010 selected **Option B (Server-held HMAC-SHA256 signatures + SHA-256 hash-chained agent audit seal)** over Option A (DB privileges only), Option C (Per-approver asymmetric PKI), and Option D (External append-only ledger). Below is the explicit scalability and maintainability assessment requested in Mid-PDR feedback:

| Dimension | Option A (DB Privileges Only) | Option B (Server-Held HMAC + Hash Chain — Chosen) | Option C (Per-Approver Asymmetric PKI) | Option D (External Ledger) |
|---|---|---|---|---|
| **Horizontal API Scalability** | Stateless; zero crypto overhead. | **Stateless across replicas** when sharing `SIP_DECISION_SIGNING_KEY` via secret manager (Fly.io/Render env). HMAC-SHA256 runs in `<0.05 ms` per transition, supporting >10,000 decisions/sec per worker — orders of magnitude above INZBC's ~5–20 gated decisions/day. | Stateless verification at API, but requires client-side WebAuthn/browser key signing + distributed CRL/OCSP revocation lookup on every read/write. | Network round-trip (50–250 ms) per write introduces external latency and availability coupling on the critical approval path. |
| **Storage & Replay Scalability** | `O(n)` log scan. | Adds one 64-char hex `decision_signature` column (`~64 bytes/row`) and one hash-chain seal per agent run. Full replay of 200 runs completes in `<1.2 s` in CI (`test_research_eval.py`). | Stores public-key cert chain + signature (`~1–4 KB/row`) + historical revocation snapshots to replay old runs after staff turnover. | External storage billing + cross-system reconciliation overhead. |
| **Maintainability & Key Rotation** | Low code complexity, but brittle operational security: depends on out-of-repo DB role grant (`database/audit_role.sql`). | **High maintainability for a 3-person team:** 1 module (`apps/sip/core/audit_seal.py`), 1 migration (`0006`), 1 secret. **Known maintainability constraint:** rotating `SIP_DECISION_SIGNING_KEY` requires a versioned key-ID (`kid`) or re-verification checkpoint before retiring the old key so historical rows remain verifiable. | High lifecycle cost: onboarding, lost-device recovery, revocation when INZBC staff leave, and security review of browser key storage — unsustainable without dedicated IT/IAM staff. | Vendor lock-in, third-party SLA/credential management, and client data residency approval overhead. |
| **Evolution Path** | Dead end for tamper-evident audit. | Clean incremental upgrade path: adding a `key_id` column enables zero-downtime key rotation, and Option C can layer on top of `decision_signature` if INZBC later mandates third-party non-repudiation. | Premature for Block 4; documented as future Phase 2 upgrade. | Unnecessary external dependency. |

---

## 3. Objective 2.1 Addendum — LLM Hallucinations: Causes, Effects & Control Evaluation

### 3.1 Causes of Hallucinations in LLM Applications
Academic and industry literature identifies four structural causes of hallucinations — outputs that are fluent yet factually unfaithful to source data or real-world facts (Ji et al., 2023; Huang et al., 2025):
1. **Next-token statistical objective & calibration gaps:** Autoregressive pre-training rewards plausible continuation rather than factual abstention; Kalai and Vempala (2024) prove mathematically that calibrated language models inevitably hallucinate on rare or arbitrary facts not densely represented in training data.
2. **Parametric vs. contextual knowledge conflict:** When retrieved context contradicts or is sparser than parametric memory, models frequently fall back to memorized priors (Lewis et al., 2020; Huang et al., 2025).
3. **Context-window degradation & prompt injection:** Long or noisy retrieved contexts dilute attention over ground-truth facts, while indirect prompt injections embedded in scraped web text can deliberately steer generation away from source truth (Greshake et al., 2023; OWASP, 2025, LLM01/LLM09).
4. **Absence of deterministic verification:** Without external grounding checks, models emit fabricated URLs, statistics, or policy claims with identical surface confidence to verified facts (Gao et al., 2023; NIST, 2023).

### 3.2 Operational Effects in the INZBC Trade Intelligence Domain
For the India–New Zealand Business Council (INZBC), unmitigated hallucinations carry severe institutional risks:
- **Reputational & diplomatic damage:** Misstating an India–NZ tariff rate, regulatory deadline, or ministerial quote in a CEO-approved daily brief or public FTA Centre answer directly undermines INZBC's credibility with government and corporate members.
- **Decision distortion:** Fabricated urgency or invented bilateral trade signals could misdirect executive council advocacy or member export planning.
- **Compliance & audit failure:** Publishing unverified claims without traceable source URLs violates SIP-184/SIP-188 editorial governance and NIST AI RMF accountability requirements (NIST, 2023).

### 3.3 Evaluation of INZBC Controls Against Hallucination Risk

| Control Layer | Mechanism Implemented in `inzbc` | Hallucination Risk Reduced | Measured / Observed Evidence | Residual Risk (Honest Limit) |
|---|---|---|---|---|
| **1. Grounded Retrieval (RAG) & Abstention** | FTA Centre (`apps/fta/`) retrieves strictly from approved FTA corpus with explicit `No Match` abstention when cosine/lexical confidence falls below threshold; SIP candidates link to real NewsAPI/RSS URLs (`#63`, `#394`, `#446`). | Reduces parametric-memory fabrication by anchoring outputs to retrieved documents (Lewis et al., 2020). | Synonym retrieval `hit@1` improved `0.20 → 1.00` (dev) / `0.50 → 0.80` (held-out); live FTA query for unindexed topic ("NZ–India cryptocurrency tax treaty") returned explicit `No Match` with `0` fabricated claims. | Outdated source corpus or ambiguous multi-clause legal questions can still yield incomplete synthesis. |
| **2. Mandatory Source Citation & Verification Gate** | Every SIP candidate stores `source_url` and `verification_status`; high-risk/critical items are structurally blocked in `apps/sip/core/state_machine.py` from brief inclusion until human-verified with evidence. | Prevents uncited claims from entering executive briefs (Gao et al., 2023). | `48/48` gate-safety attacks blocked; `4/4` control knockouts prove removing the verification gate lets unverified claims through. | A human reviewer could still attach a weak URL if not exercising diligence. |
| **3. Advisory-Only Scoring & Quality Judge + Anti-Rubber-Stamp QA** | Scoring Agent and Quality Judge (`#64`) return advisory scores only; QA Reviewer must be distinct from Drafter (server-enforced SoD `403`), must perform substantive non-trivial edits (`#553` anti-rubber-stamp guard), followed by signed CEO approval (`#448`). | Eliminates autonomous publication of hallucinated prose (Shneiderman, 2020; OWASP, 2025, LLM06/LLM09). | Live Postgres demo proved SoD `403` refusal, anti-rubber-stamp block on untouched draft, and HMAC-signed QA/CEO transitions (`200/200` forgery detection). | Automation bias (Laux & Ruschemeier, 2026) remains a human-factors risk; independent external QA calibration is still required beyond our 8-case rubric-author check (`kappa 1.0`). |

---

## 4. Objective 2.2 Addendum — Research-to-Code Traceability Matrix

| Research / Literature Finding | Repository & PRs | Concrete Implementation | Measured Before → After | Specific Value Added to INZBC |
|---|---|---|---|---|
| Control/data-flow separation (CaMeL — Debenedetti et al., 2025; Yao et al., 2022) | `inzbc` PR `#62`, `#449` | 7-tool allow-list, strict Pydantic schemas, deterministic run state machine (`apps/sip/core/`). | `48/48` attacks blocked (`4/4` knockouts); `0/35` live-model injection breaches. | Guarantees the daily coordinator can never autonomously approve or distribute an unvetted brief. |
| Cryptographic tamper-evident logs (Schneier & Kelsey, 1999) | `inzbc` PR `#448`, `ADR-0010` | HMAC-SHA256 human decision signatures + SHA-256 hash-chained agent audit seal (`audit_seal.py`, migration `0006`). | Forged decision detection: `0/200 → 200/200`; metadata tamper: `0/1000 → 1000/1000`; DB rewrite: `341/759 → 759/759`. | Gives INZBC board and auditors cryptographic proof that recorded QA/CEO approvals were not tampered with post-hoc. |
| Advisory LLM-as-judge with bias limits (Zheng et al., 2023; Liu et al., 2023; Cohen, 1960) | `inzbc` PR `#64`, `#456` | Rubric-based brief quality judge returning advisory scores only; code computes `needs_revision`. | `8/8` golden-set agreement (`kappa 1.0`, `17/17` score bounds); rubric-author check `8/8` (`kappa 1.0`). | Accelerates QA prep while preserving 100% human editorial authority. |
| Retrieval grounding & synonym expansion (Lewis et al., 2020) | `inzbc` PR `#63`, `#394`, `#446` | pgvector semantic retrieval + per-question synonym regression gate in FTA Centre. | FTA `hit@1`: `0.20 → 1.00` (dev), `0.50 → 0.80` (held-out); `No Match` abstention verified live. | Members receive accurate, source-cited FTA answers instead of dead ends or hallucinated tariff claims. |
| Productive friction against automation bias (Rubegni et al., 2026; Laux & Ruschemeier, 2026) | `inzbc` PR `#553`, `#559`, `#565` | Anti-rubber-stamp QA gate + CEO modal keyboard focus trap + real-Postgres Playwright E2E test. | Closed fail-open QA gap where untouched placeholder drafts could pass review. | Ensures human oversight is substantive rather than ceremonial. |
| Live E2E verification catches contract drift missed by mocks | `inzbc` PR `#582`, `#583`, `#584` | Fixed live Platform Assistant tool-shorthand/guide prompts (`#583`), refreshed overview scale metrics, and fixed `sponsors_persistence.py` `record_audit` kwargs bug (`#584`). | `1,792+` Python tests (`94.64%` cov), `481/481` UI tests, `82` OpenAPI ops, `30` tables all green. | Ensures the live Postgres + OpenAI platform operates reliably end-to-end for client demos and handover. |

---

## 5. Objective 3.1 Addendum — W1–W8 Team Activity Plan, Timesheets & Formal Meeting Minutes

### 5.1 Detailed W1–W8 Team Activity Plan (Block 4, 2026)

| Week | Dates | Planned Milestones & Deliverables | Owner(s) | Deadline | Actual Status & Variance |
|---|---|---|---|---|---|
| **W1** | 5–11 Oct | Kickoff, lane ownership (`bhanu.md`, `roshan.md`, `paras.md`), CI/CODEOWNERS rules, confirm PDR slots, finalize schema/API contracts. | Bhanu (Lead), Roshan, Paras | 11 Oct | Completed on time. Lanes & PR rules established. |
| **W2** | 12–18 Oct | Ship 4 flagship AI builds (`#62` Coordinator, `#63` pgvector, `#64` Judge, `#65` Streaming Comms); FTA synonym work; public site fixes. | Bhanu (`#62–#65`), Roshan (`#394`), Paras (`inzview`) | 16 Oct | Completed 16 Oct (`13` issues closed by Bhanu; all 4 AI PRs merged green). |
| **W3** | 19–25 Oct | Run agent-safety/replay baselines; draft 17-source lit review & `ADR-0010`; review & merge `#433–#446`; bring forward W6 HMAC signing (`#448`, `#449`). | Bhanu (Lead/Eval), Roshan, Paras | 24 Oct | **Ahead of schedule:** W6 HMAC signing brought forward from 9 Nov to 24 Oct after baseline exposed `0/200` forgery gap. |
| **W4** | 26 Oct–1 Nov | Client freezes live public website (`26 Oct`); reallocate Paras to AI agent UI/accessibility; draft Practice PDR worksheet & Group Mid-PDR report. | All (Bhanu coordinates reallocation) | 1 Nov | Plan updated cleanly; zero idle capacity after website freeze. |
| **W5** | 2–8 Nov | Mid-PDR presentation & feedback receipt; resolve `raw_articles` vs `exported_articles` schema contract (`#533`/`#537`); close `#291`. | All | 6 Nov | Mid-PDR completed; schema contract reconciled cleanly. |
| **W6** | 9–15 Nov | Address Mid-PDR feedback; harden QA anti-rubber-stamp gate (`#553`), modal focus trap (`#558`/`#559`), real-Postgres Playwright E2E (`#565`). | Paras (UI/QA), Roshan (FTA/Collector), Bhanu (Review/Arch) | 15 Nov | Completed; all PRs merged with green CI. |
| **W7** | 16–22 Nov | Full independent re-verification (`58d0477`), board audit (`#560`), client Go-Live Sign-Off Pack (`#582`: Sector Briefs `#194`, Sponsors `#200`), Group Final Report. | All (Bhanu `#582`, Paras `#560`/Report, Roshan evals) | 20 Nov | Completed 20–21 Nov (`1,792` Py / `481` UI tests green). |
| **W8** | 23–27 Nov | Live Postgres + OpenAI demo recording & evidence pack (`#583`), fix `sponsors_persistence` audit bug (`#584`), Individual Reflection Report & Evidence Portfolio, Final PDR & Moodle upload. | Bhanu (Individual + `#583`/`#584`), All (Final PDR) | 27 Nov, 10:30 AM | Completed & verified for submission. |

### 5.2 Weekly Progress & Individual Timesheet Summary (Bhanu Gupta)

| Week | Engineering & Code (hrs) | Research, Eval & Docs (hrs) | Code Review, Mentoring & Mgmt (hrs) | Total Hrs | Key Verified Output |
|---|---:|---:|---:|---:|---|
| W1 (5–11 Oct) | 6.0 | 2.0 | 4.0 | **12.0** | Lane contracts, CI/CODEOWNERS, backlog triage |
| W2 (12–18 Oct) | 14.0 | 2.0 | 3.0 | **19.0** | `#62`, `#63`, `#64`, `#65`, `#36`, `#38`, `engineering-answers-2026-10-16.md` |
| W3 (19–25 Oct) | 11.0 | 9.0 | 5.0 | **25.0** | `#433–#446` reviews, 17-source lit review, `ADR-0010`, `#448`, `#449`, `#456` |
| W4 (26 Oct–1 Nov) | 4.0 | 6.0 | 4.0 | **14.0** | Website-freeze replan, W4 cycle-time audit, Mid-PDR prep |
| W5 (2–8 Nov) | 5.0 | 4.0 | 5.0 | **14.0** | Team meeting (2 Nov), `#533`/`#537` contract reconciliation, Mid-PDR |
| W6 (9–15 Nov) | 4.0 | 3.0 | 5.0 | **12.0** | Review/mentoring on `#553`, `#558`/`#559`, `#565`, W6 audit |
| W7 (16–22 Nov) | 12.0 | 5.0 | 4.0 | **21.0** | `#582` (`#194`, `#200`, migration `0011`, Go-Live Pack), full CI verification |
| W8 (23–27 Nov) | 8.0 | 10.0 | 3.0 | **21.0** | Live E2E demo recording, `#583`, `#584`, Individual Reflection & Portfolio |
| **Total** | **64.0** | **41.0** | **33.0** | **138.0** | All approved engineering scope complete & CI-verified |

### 5.3 Formal Team & Client Meeting Minutes (Extracts with Actions, Owners & Dates)

1. **Meeting 1 — Sprint Kickoff & Governance Alignment (16 Oct 2026, Written + Sync)**
   - **Attendees:** Bhanu Gupta (Chair/Tech Lead), Roshan Aryal, Paras.
   - **Decisions:** Retain weekly tech-lead review cadence; decline ad-hoc review rota (`#320`) and daily GitHub check-ins (`#405`); preserve ADR-0008 analysis and `#390`/`#392`/`#406`.
   - **Actions:** (a) Bhanu to publish consolidated `docs/engineering-answers-2026-10-16.md` — *Done 16 Oct*; (b) Roshan to update `roshan-studio6-plan.md` change log — *Done 16 Oct*; (c) Paras to align `inzview` PRs with CODEOWNERS — *Done 23 Oct*.
2. **Meeting 2 — Client Scope Freeze & Reallocation (26 Oct 2026, Client Sunil + Team Sync)**
   - **Attendees:** Sunil (INZBC), Paras, Bhanu Gupta, Roshan Aryal.
   - **Decisions:** Freeze edits to live public Wix/inzview site to avoid production risk; redirect Paras's capacity to AI agent UI defects, accessibility, and E2E tests.
   - **Actions:** (a) Paras to log freeze in `docs/workstreams/paras.md` and pivot to SIP/agent UI fixes — *Done 26 Oct*; (b) Bhanu to keep `#55`/`#189` client blockers visible in weekly status reports — *Ongoing through 20 Nov*.
3. **Meeting 3 — Full Team Weekly Sync & Mid-PDR Alignment (2 Nov 2026, WhatsApp Group Call)**
   - **Attendees:** Bhanu Gupta, Roshan Aryal, Paras (verified via phone call screenshots in Group Report Fig. 17).
   - **Decisions:** Align Mid-PDR narrative on honest limitations (no live production run claimed; distinguish engineering completion from client sign-off); reconcile collector export schema (`#533` vs `#537`).
   - **Actions:** (a) Bhanu to verify baseline metrics and compile Mid-PDR safety section — *Done 2 Nov*; (b) Roshan to lock `exported_articles` schema contract with collector tests — *Done 6 Nov*; (c) Paras to review QA gate rubber-stamp literature and audit board — *Done 11–18 Nov*.
4. **Meeting 4 — Final Verification & Handover Readiness Sync (20 Nov 2026, Team Sync)**
   - **Attendees:** Bhanu Gupta, Roshan Aryal, Paras.
   - **Decisions:** Freeze independent test counts on commit `58d0477` (`1,792` Py / `481` UI); record `#55` closure-vs-evidence discrepancy honestly; ship Go-Live Sign-Off Pack (`#582`) and prepare live Postgres + OpenAI E2E demo.
   - **Actions:** (a) Paras to finalize Group Final Report & `#560` board cleanup — *Done 21 Nov*; (b) Bhanu to complete `#582`/`#583` and record full live demo with screenshots — *Done 26 Nov*; (c) All to submit individual PDR deliverables by *27 Nov, 10:30 AM*.

---

## 6. Objective 3.2 Addendum — Peer Mentoring & Conflict Resolution Logs

### 6.1 Structured Peer Mentoring & Knowledge-Sharing Log

| Date | Mentee | Technical Issue Identified | How I Explained & Guided (Rather Than Fixing Silently) | Confirmed Peer Learning & Evidence |
|---|---|---|---|---|
| **13 Oct** | Roshan Aryal | FTA synonym expansion improved aggregate score but regressed an individual product query below generic exports (`#394`). | Walked through why aggregate `hit@1` masks per-question regressions; demonstrated a per-question assertion pattern rather than just patching the score. | Roshan retained the per-question gate and independently applied regression guards across subsequent FTA/collector PRs (`#446`, `#526`–`#539`; recorded in `roshan.md` feedback log). |
| **10–14 Nov** | Paras | Initial QA anti-rubber-stamp fix (`#553`) closed the empty-edit loophole but was narrower than first described in the PR summary. | Highlighted the exact edge case during review and coached Paras on narrowing claims to match what tests actually prove instead of overriding his PR myself. | Paras authored follow-up fixes and corrected the engineering record himself (`#554`, `#557`), then independently designed and shipped the first real-Postgres Playwright approval test (`#565`). |
| **12–15 Nov** | Paras | CEO confirmation modal lacked keyboard focus trapping (`#558`) and mobile layout overflowed at `320px`. | Shared WCAG 2.2 AA focus-trap checklist and automated Playwright viewport assertion pattern so accessibility regressions would fail in CI. | Paras implemented the focus trap (`#559`) and `320px` reflow regression guard (`19090d6`) with green CI tests. |

### 6.2 Conflict Resolution Log

| Date | Conflict / Friction | Parties | Resolution Process | Outcome & Reflection |
|---|---|---|---|---|
| **16 Oct** | Unagreed process-change tickets (`#320` review rota, `#405` daily check-ins, `#406–#415`) created workflow friction and duplicated governance rules. | Roshan, Paras, Bhanu | Consolidated every proposal into one transparent written record (`docs/engineering-answers-2026-10-16.md`), keeping valuable technical analysis (`ADR-0008`, `#390`, `#392`, `#406`) while declining redundant ceremonies per `CONTRIBUTING.md`. | Tickets closed cleanly; weekly cadence preserved. *Reflection:* Stating the decision boundary and rationale earlier would have prevented the initial ticket burst. |
| **4–6 Nov** | Schema contract mismatch between collector export (`raw_articles` vs `exported_articles`, `#533` vs `#537`) risked breaking SIP ingestion. | Roshan, Bhanu | Mediated contract comparison against `schemas/api-contract.md` and `database/schema.sql`; agreed on canonical contract with automated schema tests on both repos. | Zero broken ingestion runs; cross-repo contract locked in CI. |
| **11–13 Nov** | Branch-naming drift and accidental AI-attribution strings risked violating `PROJECT-RULES.md` hygiene on shared `main`. | Team-wide | Coached teammates privately on pre-push hygiene checks and reinforced automated CI/lint guardrails rather than publicly reverting work. | Subsequent PRs (`#553–#584`) merged cleanly with compliant commits and zero rule breaches. |

---

## 7. Additional APA 7 References (Hallucination & Governance Addendum)

- Gao, L., Dai, Z., Pasupat, P., Chen, A., Chaganty, A. T., Fan, V., Zhao, V. Y., Lao, N., Lee, H., Juan, D.-C., & Guu, K. (2023). RARR: Researching and revising what language models say, using language models. In *Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)* (pp. 16477–16508). Association for Computational Linguistics. https://doi.org/10.18653/v1/2023.acl-long.910
- Huang, L., Yu, W., Ma, W., Zhong, W., Feng, Z., Wang, H., Chen, Q., Peng, W., Feng, X., Qin, B., & Liu, T. (2025). A survey on hallucination in large language models: Principles, taxonomy, challenges, and open questions. *ACM Transactions on Information Systems, 43*(2), Article 42, 1–55. https://doi.org/10.1145/3703155
- Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., Bang, Y. J., Madotto, A., & Fung, P. (2023). Survey of hallucination in natural language generation. *ACM Computing Surveys, 55*(12), Article 248, 1–38. https://doi.org/10.1145/3571730
- Kalai, A. T., & Vempala, S. S. (2024). Calibrated language models must hallucinate. In *Proceedings of the 56th Annual ACM Symposium on Theory of Computing (STOC 2024)* (pp. 160–171). ACM. https://doi.org/10.1145/3618260.3649777
- Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. In *Advances in Neural Information Processing Systems (NeurIPS 2020)* (Vol. 33, pp. 9459–9474).
- National Institute of Standards and Technology (NIST). (2023). *Artificial Intelligence Risk Management Framework (AI RMF 1.0)* (NIST AI 100-1). U.S. Department of Commerce. https://doi.org/10.6028/NIST.AI.100-1
- OWASP Foundation. (2025). *OWASP Top 10 for Large Language Model Applications (2025)*. https://genai.owasp.org/llm-top-10/
