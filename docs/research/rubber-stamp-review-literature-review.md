# Literature review: can a human-review gate on AI-generated content actually detect — or resist — a rubber stamp?

**Author:** Paras. **Status:** Annotated draft, 11 Nov 2026. Prepared with AI assistance. Every
source was checked against its real DOI/arXiv/publisher record on 11 Nov 2026, and claims are
limited to what those records state. Studio 6's course requirement to show research beyond
course work, applied directly to a real, confirmed gap: `apps/sip/ui`'s QA gate (PR #553, 10 Nov
2026) blocks a QA Pass while a report's digest sections are still untouched auto-generated
placeholder text, but Bhanu's review of it (and his own test for it) showed a trivial edit —
appending one word to the placeholder — already clears the gate. The gate proves a section was
*touched*, not that it was genuinely reviewed.

This review does not repeat the agent-safety or trust-calibration literature already covered in
`agent-safety-baseline.md` (Bhanu) or `review-approval-ui-literature-review.md` (mine, 4 Nov).
Those ask whether an agent should be trusted and how to show its reasoning; this one asks a
narrower, more mechanical question: once a human-approval step exists, what makes that step
*substantive* rather than procedural, and is "require an edit" a defensible proxy for that at
all?

## 1. The problem has a name, and a legal deadline, but no settled empirical answer

Laux & Ruschemeier, "Automation Bias in the AI Act: On the Legal Implications of Attempting to
De-Bias Human Oversight of AI" (arXiv [2502.10036](https://arxiv.org/abs/2502.10036), *European
Journal of Risk Regulation*, 2025), analyse Article 14 of the EU AI Act, which requires human
oversight of high-risk AI systems and explicitly names automation bias — over-reliance on an
AI's output — as the risk overseers must be made aware of. Their point most relevant here: it is
the *only* psychological bias the Act names, despite overseers being subject to others (e.g.
confirmation bias, time pressure), and proving that automation bias caused a specific real
oversight decision to go wrong is both legally and empirically hard, because the "correct"
unbiased outcome is usually unknown even in hindsight. They call for more empirical work on what
actually counts as effective de-biasing. Read directly: there is no established, validated
technique this project could just adopt — the regulatory expectation (meaningful human oversight)
outruns the evidence for how to build it.

## 2. Showing the AI's reasoning does not reliably fix it

Romeo & Conti, "Exploring automation bias in human–AI collaboration: a review and implications
for explainable AI" (*AI & Society*, DOI
[10.1007/s00146-025-02422-7](https://link.springer.com/article/10.1007/s00146-025-02422-7),
2026), a PRISMA-style systematic review, found that explainability/transparency mechanisms
frequently fail to reduce automation bias or improve decision accuracy — and that an overly
technical or overly simplistic explanation can *reinforce* misplaced trust, particularly for
less-experienced users. Directly relevant: this project's platform assistant and Comms Assistant
both already show their reasoning/sources as a design choice (per `docs/inzbc-ai-operating-system.md`
and this week's own research), on the assumption that visibility builds calibrated trust. This
source is a caution against treating that visibility as sufficient on its own for the *approval*
step specifically — it may help a user judge an answer, but review found no reliable evidence it
stops a reviewer from rubber-stamping an approval they were already inclined to grant.

## 3. The most directly on-point finding: effort asymmetry is what causes rubber-stamping

Rubegni, Natali, Valsecchi, Rizzo, Ayoub & Facchini, "From Oracles to Productive Friction:
Designing for Meaningful Human Oversight in Clinical AI" (*Proceedings of the AAAI/ACM Conference
on AI, Ethics, and Society* 9(3), 2206–2218, 2026, DOI
[10.1609/aies.v9i3.43300](https://ojs.aaai.org/index.php/AIES/article/view/43300)), is a
mixed-methods study with 11 radiologists comparing a single-diagnosis ("oracle") AI interface
against one presenting multiple differentials. Their core argument: when *accepting* an AI
recommendation takes less effort than *disagreeing* with it, review degrades into rubber-stamping
— and this is a direct, named finding, not an inference I am drawing. They propose "productive
friction": calibrating the interaction cost of acceptance to the case's actual uncertainty, so an
easy case stays easy and a genuinely uncertain one demands more from the reviewer. Applied to this
project's QA gate: a single "Edit → type anything → Done" step is the oracle pattern they found
insufficient, exactly as Bhanu's test demonstrated. A friction-based redesign (e.g. scaling what's
required by the SIP-188 checklist's own Critical flags, or requiring a short justification on
specifically Critical/High sections) is their proposed direction, not something this review is
recommending be built today — it is sized like a design decision for the team, not a daily fix.

## 4. A genuinely technical candidate exists for measuring edit depth, but it is not proven for this use case

Thai, Emi, Masrour & Iyyer, "EditLens: Quantifying the Extent of AI Editing in Text" (arXiv
[2510.03154](https://arxiv.org/abs/2510.03154), accepted ICLR 2026), trains a regression model on
lightweight similarity metrics between AI-generated and human-edited text to estimate the
*magnitude* of editing on a graded scale, not just a binary "was it touched." They report
F1 = 94.7% on binary human-vs-AI-edited classification and F1 = 90.4% on a three-way
human/AI-edited/AI-generated split. This is the closest thing found to a technical mechanism that
could distinguish "appended one word" from "substantially rewritten" — but it is a general text-
provenance classifier, not validated against an approval-gate use case, and running it would add
a model dependency this project does not currently have anywhere in `apps/sip/ui`. Noting it as a
candidate worth a future spike, not proposing it be adopted now.

## What I could not find

No peer-reviewed source empirically testing "require a written justification before approval" as
a friction mechanism specifically for AI-content approval gates (as opposed to source 3's clinical
diagnosis override friction). Searches for this surfaced only practitioner blog posts, which I am
not citing per this project's own research standard of checking a source's real record before
citing it.

## What this means for the SIP-188 QA gate

Not a recommendation to build something today. Three options the team can weigh, in increasing
cost: (a) leave the current touched/untouched gate as a floor and accept its known limit, since it
already stops the worst case (zero review at all); (b) require a short, separate justification
field alongside each section's edit, cheap to add, informed by source 3's effort-asymmetry
finding rather than source 2's (now-doubtful) assumption that visibility alone suffices; (c) a
longer-term, unproven technical measure (source 4) scoring edit substance, which would need its
own validation before trusting it as a gate. Raising this at standup rather than picking one
solo — it is a product/process decision about how much friction QA review should carry, not an
engineering bug.
