# Literature review: reviewer-approval UI for AI-drafted content

**Author:** Paras. **Status:** Annotated draft, 4 Nov 2026. Prepared with AI assistance. Every
source was checked against its arXiv record or publisher page on 4 Nov 2026, and claims are
limited to what those records state. Studio 6's course requirement to show research beyond
frontend/backend work, applied directly to a real, confirmed gap: #60 ("Comms Assistant review UI
with the named-reviewer approval gate") was closed on GitHub on 18 Aug 2026, but no reviewer
screen was ever built — `services/api/comms.py` has a real `POST /drafts/{id}/approve`, and
`apps/comms/ui`'s `CommsAssistant.tsx` has no diff view, no approval control, nothing that calls
it (confirmed Tuesday, PR #519). `docs/final-handover-2026-11-04.md` now lists this as an item
that passes to INZBC open, unchanged.

This review does not repeat Bhanu's `agent-safety-literature-review.md` (agent constraints) or
my own `agent-transparency-ui-literature-review.md` from last week (showing what an agent already
did, after the fact). This one is upstream of both: the question is what the screen should look
like *before* a human decision is recorded, when the thing being reviewed is a block of AI-drafted
prose rather than an agent's tool-call trail.

## 1. Introduction: the question

#60's own acceptance criterion is "the publish action is disabled until a reviewer is recorded."
That is a backend fact already true (`refuse_self_review`, `apps/comms/draft.py`). What does not
exist is the screen a reviewer would use to decide whether to approve. Three questions:

1. Is reviewing an AI-drafted diff the same kind of task as reviewing a diff in general, or does
   it need something different?
2. What happens to an approval gate that a human clicks through routinely — does it stay a real
   check?
3. What does the separation-of-duties literature say the UI owes the backend enforcement that
   already exists here?

## 2. Reviewing an LLM-generated change is a trust problem, not a diffing problem

Heander, Sergeyuk, Zakharov, Söderberg and Mukhortov, "Trust-Calibrated Code Review: A
Participatory Design Study of Review Workflows for LLM-Generated Multi-File Changes" (arXiv
[2606.01969](https://arxiv.org/abs/2606.01969), submitted to ESEM SEIP 2026 — a submission, not a
confirmed publication). Run with JetBrains: a double-diamond participatory design study, 17
practitioners in Discover, 7 returning for Develop, a follow-up survey of 43 practitioners on the
resulting prototype. Their core conclusion, stated directly: **"Reviewing LLM-generated multi-file
changes is a trust-calibration problem rather than a diffing problem."** Three workflow levels
(overview, file analysis, snippet review) each scored above the neutral midpoint (3.50–3.91 of 5);
63% of respondents expected reduced review effort, 52% expected reduced trust-assessment effort,
versus their current tools.

**What this means for #60.** The planned screen ("draft view with diff-against-previous") was
scoped as a diffing feature. This paper's subjects were reviewing code, not prose, and the paper
is a workshop submission, not yet a confirmed publication — the generalisation to a one-paragraph
Comms draft is mine, not theirs. But the shape of the finding transfers: a reviewer of an
AI-drafted LinkedIn post or newsletter is not checking "what changed" so much as "do I trust this
sentence enough to put my name on it." A plain diff-against-previous (what #60 originally asked
for) answers the first question and not the second.

## 3. Local, in-place review over whole-version rollback

Vaithilingam, Kim, Acosta-Parenteau, Lee, Mhedhbi, Glassman and Arawjo, "Semantic Commit: Helping
Users Update Intent Specifications for AI Memory at Scale" (arXiv
[2504.09283](https://arxiv.org/abs/2504.09283), cs.HC, no venue stated — an arXiv preprint). A
12-person within-subjects study on an interface where users commit new intent and the AI detects
conflicts with an existing specification, covering game design documents and ChatGPT-style AI
memories. Confirmed finding: even though a global revision/rollback feature was available, about
half the participants instead used the tool's local impact-analysis path — flagging conflicts and
resolving them in place rather than reverting a whole version.

**What this means for #60.** `comms_drafts` is append-only by design (a correction supersedes, it
never overwrites), so "revert the whole draft" was never on the table here regardless. What this
paper adds is a reason to prefer a reviewer screen that can show one proposed sentence or
paragraph in context rather than only a top-to-bottom full-document diff — the thing about half
this study's participants reached for even when a simpler, cruder whole-version option existed.

## 4. Oversight is often a downstream check, not a design requirement

Jerry, Moreno and Martínez, "Human Oversight-by-Design for Accessible Generative IUIs" (arXiv
[2602.13745](https://arxiv.org/abs/2602.13745), cs.HC; accepted for CEUR Workshop Proceedings, IUI
Workshops 2026). About LLM-generated interfaces in healthcare communication, not Comms drafting —
a different domain, cited for its general argument. Confirmed finding: oversight is "often treated
as a downstream check," with no clear rules for when a human must intervene or who is accountable
for the decision. Their proposed alternative, "oversight-by-design," embeds escalation policies
and explicit UI controls for flagging risk throughout the pipeline, not only at the end, plus
traceable audit logs of what the review feedback changed.

**What this means for #60.** This is close to #60's exact current shape, named by a different
paper about a different domain: the approval *endpoint* is a downstream check (it exists, it is
enforced, `refuse_self_review` works) — but with no screen, there is no UI-level rule surfacing
*when* a human must look, and no visible record a reviewer could point to afterward beyond the
database row. The paper's call for a traceable audit log is already met here
(`comms_draft.approve`'s audit row); its call for explicit UI controls is the part that is
missing.

## 5. Separation of duties is a role question the backend already answers; the literature is silent on the UI question

*Authorization in Action* and *Grokking Web Application Security* (both Manning Publications Co.,
via [livebook.manning.com](https://livebook.manning.com/learn/concepts/four-eyes-principle--pattern))
describe the four-eyes principle / separation of duties as requiring a sensitive action to be
reviewed by a second, distinct person before it takes effect — assigning authoring, review and
approval to different roles so "no single person performs all conflicting responsibilities."
Checked directly: neither book's referenced page states whether this must be enforced at the
backend or only surfaced in the UI.

**What this means for #60.** The silence is itself informative, not a gap in my search. This
codebase already made that call correctly and said so in writing: `apps/comms/draft.py`'s own
comment states the UI hiding an approve button for the requester is not the control —
`refuse_self_review` at the API layer is. The reviewer screen #60 needs is therefore free to focus
entirely on helping a second person *decide well*, since the separation itself is not the screen's
job to enforce.

## 6. What a named academic source for "approval fatigue" would need to establish — not found

Searched specifically for peer-reviewed evidence that a review gate degrades into rubber-stamping
under repetition (relevant because #60's reviewer would see every Comms draft, routinely). Found
only practitioner blog posts repeating an unsourced "93% of approvals are rubber-stamped" figure
and a reference, itself unverified in the search results, to Tariq et al., *Alert Fatigue in
Security Operations Centres* (claimed ACM Computing Surveys, 2025) and a Google DeepMind *AI Agent
Traps* report (claimed 2025). I did not fetch either directly and cannot confirm they say what the
blog posts attribute to them, so I am not citing them as sources — only naming the search as a
genuine "not found," per this review's own standard, rather than citing an unverified number.

## 7. Concrete finding to act on

If #60 is picked up (it is currently only recorded as open, in `docs/final-handover-2026-11-04.md`
and `docs/workstreams/paras.md`, not scheduled), build the reviewer screen around §2 and §4's
finding together: show the proposed paragraph with enough context to judge trust (not a bare
diff), and make the approval control itself visible and specific — who is approving, what they are
approving, recorded where a later reader can find it — rather than a single generic "Approve"
button bolted onto the existing drafting screen.
