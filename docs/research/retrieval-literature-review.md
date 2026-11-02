# Literature review: retrieval for governed AI

**Authors:** Roshan Aryal and Bhanu Gupta. Section 5 annotations expanded by Bhanu Gupta,
23 Oct 2026. **Status:** Annotated draft; evaluation caveat and one venue/year correction updated
26 Oct 2026.
The 26 Oct update does not claim full-text verification of sources that were previously checked
only through publisher records or abstracts. Bibliographic record of all
12 sources checked 14 Oct 2026 (section 6). Annotated bibliography due W4 (26 to 30 Oct).
Studio 6 objective 2.1, applied in 2.2 through `apps/fta/eval/`.

A checked row means the citation was compared with the publisher, Crossref, DataCite, arXiv,
proceedings, or standards page named in section 6. It does not mean the 150-word annotation is
written. Two claims in the 14 Oct notes were not in the text that was opened. They are marked
in the notes and are not cited as findings.

## 1. Introduction: why retrieval matters for INZBC

The FTA Explainer answers member questions about the NZ-India Free Trade Agreement. It may only
say what a confirmed, cited corpus entry says, and it must send anything it cannot match to INZBC
instead of guessing (`docs/modules/fta-centre.md`). So the quality of the whole service depends
on one step: finding the right entry for the question.

Today that step is a weighted keyword match with IDF weighting over 23 entries
(`apps/fta/explainer.py`). The baseline eval on 13 Oct (`apps/fta/eval/results/baseline.json`)
shows where it works and where it does not:

| Question type | n | hit@1 | MRR |
|---|---|---|---|
| Exact wording | 18 | 1.000 | 1.000 |
| Multi-term | 8 | 0.750 | 0.875 |
| Synonyms the corpus does not use | 10 | 0.200 | 0.200 |
| Must return no match | 6 | no-match accuracy 1.000 | — |

A member who asks about "lamb" or "international students" gets nothing, even though the corpus
covers sheepmeat and student visas. This review asks three questions:

1. Which retrieval methods could close the synonym gap, and what do they cost?
2. How do you ground an answer in retrieved text and evaluate it?
3. How do you keep provenance, so every answer can be traced to a verified source?

## 2. Key theories and technologies

### 2.1 Lexical retrieval: TF-IDF and BM25

Lexical methods score a document by the query terms it shares, weighted by how rare each term
is. BM25 (Robertson & Zaragoza, 2009) is the standard lexical baseline. The usual account of it
adds two corrections to plain TF-IDF: term frequency saturates, so the tenth repeat of a word
adds little, and long documents are normalised so they do not win on length alone. The 14 Oct check did not reread the BM25 article, but a 30 Oct source-passages
check verified saturation in its section 3.4.2 and length normalisation in section
3.4.5 (section 6). Manning et al. (2008) cover the
TF-IDF and vector-space model the current Explainer is built on. The book site confirms the
citation and that chapter 6 is term weighting. The chapter text was not re-read.

The strength is that lexical retrieval is transparent and cheap, and a score can be explained
term by term. The weakness is the vocabulary mismatch problem: no shared word means no match.
That is the synonym result in the baseline.

### 2.2 Dense retrieval: embeddings

Dense retrieval encodes the question and each passage as vectors and ranks by similarity.
Karpukhin et al. (2020) trained a BERT dual encoder on question-passage pairs (Dense Passage
Retrieval, DPR) and beat BM25 on top-20 passage accuracy across several open-domain QA sets.
Because the match is on meaning, "lamb" can land near "sheepmeat".

The limit is generalisation. BEIR (Thakur et al., 2021) tested retrievers zero-shot across 18
datasets and found BM25 a strong baseline that many dense models failed to beat outside the
domain they were trained on. INZBC has no training pairs, so any embedding model would be used
zero-shot, which is exactly the setting where BEIR found dense retrieval least reliable.

### 2.3 Hybrid retrieval

Hybrid retrieval runs a lexical and a dense retriever and fuses the two rankings. Reciprocal Rank
Fusion (Cormack et al., 2009) combines lists using rank alone, so the two score scales do not
need calibrating. Bruch et al. (2024) compared fusion functions and found that a convex
combination of normalised scores can beat RRF when some tuning data exists.

For INZBC the attraction is that exact-wording questions keep their lexical match, which scores
1.000 today, while synonyms gain a second route in.

### 2.4 Retrieval-augmented generation (RAG)

Lewis et al. (2020) joined a dense retriever to a sequence-to-sequence generator, so the model
writes its answer conditioned on retrieved passages rather than only on what it memorised. On
language generation tasks they report more specific, diverse and factual output than a
parametric-only sequence-to-sequence baseline. Gao et al. (2023) survey the field since then and
group systems into naive, advanced and modular RAG. Advanced RAG is the group in which they
place the work on retrieval quality, through pre-retrieval and post-retrieval steps.

The Explainer is deliberately not RAG in the generation sense. It returns the corpus entry
itself, with no model writing prose. The retrieval half of this research applies directly. The
generation half applies to the Comms Assistant and SIP briefs, not to the FTA answers.

### 2.5 Evaluating retrieval and RAG

Ranked retrieval is measured with hit@k and mean reciprocal rank (Manning et al., 2008), which
is what `apps/fta/eval/` reports. RAGAs (Es et al., 2024) proposes reference-free scores for a
whole RAG pipeline: faithfulness (is the answer supported by the retrieved context), answer
relevance, and context relevance. These are judged by a language model.

For the FTA corpus a hand-labelled question set is affordable and more trustworthy than a model
judge. RAGAS-style faithfulness is more relevant to issue #64 (LLM-as-judge for briefs).

### 2.6 Provenance and governance

W3C PROV-DM (Moreau & Missier, 2013) models provenance as entities, the activities that
generated or used them, and the agents responsible. It provides relations such as
`wasDerivedFrom` and `wasAttributedTo`. The NIST AI Risk Management Framework (NIST, 2023)
organises AI risk work into Govern, Map, Measure and Manage. It lists "valid and reliable" and
"accountable and transparent" among the marks of trustworthy AI.

Each corpus entry already carries a citation, a source tier and a verified date. That is
provenance in all but name. PROV-DM gives a standard vocabulary for it. NIST's Measure function
is what a committed eval set and a before vs after score provide.

## 3. Comparison and evaluation

| Approach | How it works | Strength | Weakness | Fit for the 23 FTA entries |
|---|---|---|---|---|
| Original keyword TF-IDF baseline (before #383; original evaluation set) | Shared terms weighted by rarity | Transparent, no dependencies; original exact wording hit@1 1.000 | No match without a shared word; historical development synonym hit@1 was 0.200 before the synonym map | Historical comparator only; the current lexical `answer_query()` includes the #383 synonym map, with development synonym hit@1 1.000 |
| BM25 | TF-IDF with saturation and length normalisation. That account of the 2009 article was not re-read on 14 Oct (section 6) | Robust zero-shot baseline (BEIR abstract) | Same vocabulary gap. A rare framing word can outweigh the product | Measured worse (#398): 0.333 hit@1 on product plus framing questions, where "exports" outweighs "dairy" |
| Keyword plus synonym list | Expand the query with terms of a similar meaning (Carpineto & Romano, 2012) | Explainable, no model call, cheap to test | The list has to be maintained by hand, and misses terms nobody listed. On this corpus an ambiguous added term can point at another topic. That limit is from #383, not from the survey abstract | Built (#383). Synonym hit@1 0.200 to 1.000, no-match unchanged |
| Dense embeddings | Rank by vector similarity | Matches meaning, so it handles synonyms | Zero-shot reliability (BEIR). Needs a model, which may cross the model data boundary in ADR-0006 | Possible, but must not lose an exact or no-match result |
| Hybrid (RRF) | Fuse lexical and dense rankings | Can combine exact-wording and semantic matches; performance is unmeasured here | Two systems to run. Without a validated similarity cut-off, no-match queries risk false answers | #63 delivered embedding infrastructure, not approval of a production hybrid ranker; evaluate via #393 first |

The deciding risk for INZBC is not the miss but the false answer. A dense retriever ordinarily
returns its nearest neighbour, even for "steel" or "pharmaceuticals", which the corpus does not
cover. Today those return no match and route to INZBC (no-match accuracy 1.000 on the ten
current development questions). A threshold must be chosen using development evidence, then
validated on **different, independently labelled no-match questions**. Choosing the threshold
against the same ten rows reported as its test would inflate apparent reliability.

## 4. What this means for the project

1. **Measure first.** Done (#382). The set has since grown to 55 questions, plus a 10-question
   held-out synonym set (#390).
2. **Cheapest change first:** a curated synonym map inside `apps/fta`, with no model call. Done
   (#383): synonym hit@1 went from 0.200 to 1.000. The map left out "log", "baby" and "travel"
   because those words point at more than one topic. That was a project choice. Carpineto and
   Romano (2012) are the survey behind the method. Their abstract does not state this drift
   warning, so it is not cited as theirs (section 6).
3. **BM25 measured, not assumed (#398).** BEIR's finding that BM25 is a strong baseline did not
   hold for this corpus. With one short topic per entry, a framing word that appears in only one
   topic ("exports") gets a high IDF and outranks the product, so BM25 scored 0.333 on product
   plus framing questions against 1.000 for the live ranker. A general benchmark result did not
   transfer to a 23-entry corpus, which is why every candidate is scored on our own questions.
4. **Evaluate embeddings, do not assume they win.** #63's shared server-side embedding path
   is now implemented, but its availability is not a production-ranking decision. #393 remains
   open; PR #469 proposes an *offline* comparison using actual provider-generated scores,
   a preselected threshold and hybrid RRF, without changing `answer_query()`.
5. **Compare on equivalent evidence.** Report the existing keyword, keyword plus synonyms and
   BM25 variants with dense and hybrid on matched question sets, separately by query type;
   include no-match accuracy, provenance, label-check status and held-out limitations in W7.
   No dense or hybrid measured score is claimed by this draft.
6. **What does not apply:** training a DPR model (no labelled pairs, and 23 entries do not
   justify it), and RAG generation for FTA answers (the Explainer must quote the corpus, not
   paraphrase it).


### 4.1 Measurement independence and falsifiable acceptance (26 Oct 2026)

The lexical comparison has two distinct sources of evidence; merging them into one large
average would conceal how the query expansion was developed. The **55-question development set**
(`apps/fta/eval/questions.csv`) includes 18 exact, 8 multi-term, 10 synonym,
10 no-match and 9 product-framing queries. The synonym map was written after seeing the original
ten synonym cases, so the perfect in-sample synonym score is a fit-to-development result,
not an independent replication.

Paras separately authored ten synonym questions (`held_out_questions.csv`). The live keyword
ranker achieves **8/10 = 0.800** on that historical set. A query-text audit found two exact
overlaps with the development queries: H03/Q27 ("milk powder") and H04/Q31 ("baby formula").
After excluding those duplicates, the same ranker scores **6/8 = 0.750**. Both numbers are
reported, because retroactively discarding questions cannot recreate a fully unseen dataset.
The eight unique questions remain too few, and too homogeneous, to estimate production
accuracy for member traffic. These are **repository experiment results**, not claims made by
the twelve external publications.

| Evidence set | n | Keyword hit@1 | Can test independent no-match? |
|---|---:|---:|---|
| Historical separately authored synonym set | 10 | 0.800 | No |
| Query-distinct subset, after overlap audit | 8 | 0.750 | No |

Sources for these exact numbers and overlaps:
`apps/fta/eval/results/variants-held-out.json`,
`apps/fta/eval/results/variants-held-out-nonoverlap.json` and
`apps/fta/eval/results/held-out-overlap.json`. No new scores were produced for this note.

To choose a new retrieval method without marking its own homework, an evaluation should (a)
specify the embedding model, corpus version, document/query representation and similarity
threshold *before* opening held-out labels; (b) record the actual result IDs and cosine scores
from the approved, redacted server-side path; (c) compare rankers on the same inputs, breaking
down lexical exact matches, synonyms, product-framing and no-match; and (d) have a named
independent human verify expected IDs. Issue #406 was closed on 23 Oct, but the
`checked_by` column of the development CSV is still blank, so the ten-check acceptance
evidence must not be inferred from issue status. The #439 protocol is not completed review.

Until independent no-match and product-framing test cases and real gateway measurements are
available, the justified choice is **retain the measured lexical ranker**, not declare hybrid
better based on a general retrieval paper. This is an evaluation recommendation, not a
production architecture approval.


## 5. Annotated bibliography

Twelve annotations follow, each in four parts: reference, summary, evaluation and application to
INZBC. The check of each source against its original is in section 6.

| # | Source | Type | Checked against original | Annotation done |
|---|---|---|---|---|
| 1 | Robertson & Zaragoza (2009) | Peer-reviewed | 14 Oct 2026, citation | 23 Oct 2026 |
| 2 | Manning, Raghavan & Schütze (2008) | Textbook | 14 Oct 2026, citation | 23 Oct 2026 |
| 3 | Karpukhin et al. (2020) | Peer-reviewed | 14 Oct 2026, citation and abstract | 23 Oct 2026 |
| 4 | Thakur et al. (2021) | Peer-reviewed | 14 Oct 2026, citation and abstract | 23 Oct 2026 |
| 5 | Cormack, Clarke & Büttcher (2009) | Peer-reviewed | 14 Oct 2026, citation | 23 Oct 2026 |
| 6 | Bruch, Gai & Ingber (2024) | Peer-reviewed | 14 Oct 2026, citation and abstract | 23 Oct 2026 |
| 7 | Lewis et al. (2020) | Peer-reviewed | 14 Oct 2026, citation and abstract | 23 Oct 2026 |
| 8 | Gao et al. (2023) | Preprint survey | 14 Oct 2026, citation and section headings | 23 Oct 2026 |
| 9 | Es et al. (2024) | Peer-reviewed conference demo (EACL 2024) | 14 Oct arXiv; 26 Oct ACL Anthology bibliographic record and abstract | 23 Oct 2026; corrected 26 Oct |
| 10 | Moreau & Missier (2013) | Standard | 14 Oct 2026, recommendation text | 23 Oct 2026 |
| 11 | NIST (2023) | Framework | 14 Oct 2026, PDF | 23 Oct 2026 |
| 12 | Carpineto & Romano (2012) | Peer-reviewed survey | 14 Oct 2026, citation and abstract | 23 Oct 2026 |

### Annotations (23 Oct 2026)

Each annotation has four parts: reference, summary, evaluation and application to INZBC. What was
checked against each original, and what was not, is recorded once in section 6. Nothing here goes
beyond those checks. Project results are cited to their issue or PR, not to the source.

**1. Robertson & Zaragoza (2009).**
*Reference.* Robertson, S., & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and
beyond. *Foundations and Trends in Information Retrieval, 3*(4), 333-389.
https://doi.org/10.1561/1500000019
*Summary.* The monograph sets out the probabilistic relevance framework by the authors of BM25,
the ranking function it leads to. It is the standard reference for scoring a document by the
query terms it contains, weighted by how rare they are.
*Evaluation.* It is authoritative on the method because its authors wrote it. It is a theory
monograph, not a benchmark, so it says what BM25 is, not how well it does on a given corpus.
*Application.* BM25 was implemented and measured in #398. On product plus framing questions it
scored 0.333 hit@1 against 1.000 for the live ranker, because the rare word "exports" outweighed
"dairy". So BM25 stays a measured comparator and not a replacement.

**2. Manning, Raghavan & Schütze (2008).**
*Reference.* Manning, C. D., Raghavan, P., & Schütze, H. (2008). *Introduction to information
retrieval*. Cambridge University Press. https://nlp.stanford.edu/IR-book/
*Summary.* The textbook covers term weighting and the vector space model (chapter 6) and the
evaluation of ranked retrieval (chapter 8). These are the basic ideas behind keyword ranking and
the measures used to judge it.
*Evaluation.* It is a textbook, not new research. It is the accepted reference for the basics,
and it will not settle which method suits a particular corpus.
*Application.* The live FTA ranker in `apps/fta/explainer.py` weights shared terms by rarity, and
`apps/fta/eval/run_eval.py` reports hit@1, hit@3 and mean reciprocal rank. Both come from these
chapters. The book defines the measures. Whether a gain carries over to new questions is a
separate question, answered by the held-out set (#390) and independent label checks (#406).

**3. Karpukhin et al. (2020).**
*Reference.* Karpukhin, V., Oguz, B., Min, S., Lewis, P., Wu, L., Edunov, S., Chen, D., & Yih,
W. (2020). Dense passage retrieval for open-domain question answering. In *Proceedings of the
2020 Conference on Empirical Methods in Natural Language Processing* (pp. 6769-6781).
https://doi.org/10.18653/v1/2020.emnlp-main.550
*Summary.* Dense Passage Retrieval trains two encoders on question and passage pairs and ranks
passages by vector similarity. The abstract reports top-20 retrieval accuracy 9 to 19 percentage
points above Lucene-BM25 on open-domain question answering.
*Evaluation.* The gains are large, but they come from training on many labelled pairs, inside the
domain being tested.
*Application.* INZBC has 23 short entries and no labelled training pairs, so training a retriever
is out. A pre-trained embedding model used zero-shot is the only realistic option. It would need
approval under #63 and the model data boundary, and it would have to keep exact-wording and
no-match results.

**4. Thakur et al. (2021).**
*Reference.* Thakur, N., Reimers, N., Rücklé, A., Srivastava, A., & Gurevych, I. (2021). BEIR: A
heterogeneous benchmark for zero-shot evaluation of information retrieval models. In
*Proceedings of the Neural Information Processing Systems Track on Datasets and Benchmarks*.
https://arxiv.org/abs/2104.08663
*Summary.* BEIR tests retrievers zero-shot across 18 datasets. The abstract finds BM25 a robust
baseline, and many dense models do worse outside the domain they were trained on.
*Evaluation.* Its breadth makes it a good guard against choosing a retriever on one favourable
benchmark. It is a general finding, and it does not claim BM25 is best on every corpus.
*Application.* #398 is a case where the general result did not hold. On a 23-entry corpus with one
short topic each, BM25 lost to the live ranker on product plus framing questions. The lesson for
#63 is that any embedding model has to beat the live ranker on our own questions, including the
held-out set, not on BEIR.

**5. Cormack, Clarke & Büttcher (2009).**
*Reference.* Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal rank fusion
outperforms Condorcet and individual rank learning methods. In *Proceedings of the 32nd
International ACM SIGIR Conference on Research and Development in Information Retrieval* (pp.
758-759). https://doi.org/10.1145/1571941.1572114
*Summary.* Reciprocal Rank Fusion merges several ranked lists using only each item's rank. As its
title states, the paper compares it with Condorcet fusion and individual rank-learning methods.
*Evaluation.* It is a two-page SIGIR paper, but the method is simple and widely reused. Its
attraction is that it needs no score calibration between systems.
*Application.* RRF is the obvious first way to combine the live ranker with an embedding ranker
under #393, since their scores are on different scales. Fusion alone does not stop a wrong answer
ranking first. Any hybrid also needs a similarity cut-off, or the ten no-match questions start
returning answers.

**6. Bruch, Gai & Ingber (2024).**
*Reference.* Bruch, S., Gai, S., & Ingber, A. (2024). An analysis of fusion functions for hybrid
retrieval. *ACM Transactions on Information Systems, 42*(1), Article 20.
https://doi.org/10.1145/3596512
*Summary.* The paper compares ways of fusing lexical and dense results. The abstract reports that
a convex combination of normalised scores outperforms RRF in and out of domain, and that RRF is
sensitive to its own parameter.
*Evaluation.* It is a careful, recent journal study and a useful check on treating RRF as the
default. The convex combination's gain depends on having data to set its weight.
*Application.* INZBC has 23 corpus entries and 55 labelled questions (`apps/fta/eval/questions.csv`),
so tuning fusion weights on that set risks fitting the evaluation rather than the task. RRF, with
its fixed rule, is the safer first comparison. A tuned convex combination would need to be judged
on the held-out questions (#390).

**7. Lewis et al. (2020).**
*Reference.* Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H.,
Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented
generation for knowledge-intensive NLP tasks. In *Advances in Neural Information Processing
Systems 33*.
https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html
*Summary.* The paper that named RAG joins a dense retriever to a generator, so answers are
written from retrieved passages. On generation tasks the abstract reports more specific, diverse
and factual language than a parametric-only baseline.
*Evaluation.* It is foundational for separating finding evidence from writing an answer. It is
not evidence that every retrieval system should generate text.
*Application.* The FTA Explainer returns the corpus entry and its citation and writes no prose, so
the retrieval half applies and the generation half does not. Generation fits the Comms Assistant
and SIP briefs, where drafts already need human review.

**8. Gao et al. (2023).**
*Reference.* Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., Wang, M., &
Wang, H. (2023). *Retrieval-augmented generation for large language models: A survey*
(arXiv:2312.10997). arXiv. https://doi.org/10.48550/arXiv.2312.10997
*Summary.* The survey groups RAG systems since Lewis et al. into naive, advanced and modular RAG.
Advanced RAG is where it places pre-retrieval and post-retrieval work on retrieval quality.
*Evaluation.* It is a preprint survey. That makes it useful as a map of the field, not as
evidence for any single result. An earlier note claimed it called retrieval quality the main
lever on answer quality. That sentence is not in the text checked, so it is not used.
*Application.* The grouping places the FTA work in the retrieval stage. The decision to measure
retrieval first comes from the project's own baseline, where synonym hit@1 was 0.200, not from
this survey.

**9. Es et al. (2024).**
*Reference.* Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2024). RAGAs: Automated
evaluation of retrieval augmented generation. In *Proceedings of the 18th Conference of the
European Chapter of the Association for Computational Linguistics: System Demonstrations*
(pp. 150–158). Association for Computational Linguistics.
https://doi.org/10.18653/v1/2024.eacl-demo.16
*Summary.* RAGAs proposes reference-free evaluation for retrieval-augmented generation,
separating retrieval relevance, how faithfully a generator uses its context, and the quality of
the generated answer. Its EACL abstract describes evaluation without human-labelled ground truth.
*Evaluation.* This is a peer-reviewed EACL 2024 system-demonstration paper, not solely a 2023
preprint. The metrics still depend on automated evaluation and must be validated against humans
where unsupported answers are consequential. The 26 Oct verification covered the ACL Anthology
bibliographic record and abstract, **not** a new review of the entire paper body.
*Application.* The FTA Explainer returns cited corpus entries rather than generating prose; its
entry-ID and no-match eval is more direct than model-judged answer faithfulness. RAGAs is more
relevant to #64's generated SIP briefs, but it would supplement, not replace, human QA.

**10. Moreau & Missier (2013).**
*Reference.* Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model* (W3C
Recommendation). World Wide Web Consortium. https://www.w3.org/TR/prov-dm/
*Summary.* PROV-DM models provenance as entities, the activities that used or produced them and
the agents responsible. It names relations such as `wasDerivedFrom` and `wasAttributedTo`.
*Evaluation.* It is a W3C Recommendation, so it is authoritative but abstract. It supplies a
vocabulary for provenance, not evidence about any retrieval method.
*Application.* Each FTA corpus entry already carries a citation, a source tier and a verified date,
which is provenance in all but name. PROV-DM gives those fields standard names, if INZBC ever needs
to show source-to-answer lineage outside the code. What matters now is narrower: stable entry IDs,
source facts kept apart from inference, and the citation and effective date shown with each
answer. Adopting PROV formally would be a separate, scoped decision.

**11. NIST (2023).**
*Reference.* National Institute of Standards and Technology. (2023). *Artificial intelligence risk
management framework (AI RMF 1.0)* (NIST AI 100-1). https://doi.org/10.6028/NIST.AI.100-1
*Summary.* The framework organises AI risk work into four functions: Govern, Map, Measure and
Manage. It names "valid and reliable" and "accountable and transparent" among the marks of
trustworthy AI.
*Evaluation.* It is a government framework, not research, and it is voluntary. Its value is the
shared structure it gives to connecting technical evidence with accountability.
*Application.* In this project the committed question set and the CI eval gate (#394) are the
Measure function in practice, and the human approval gates are Govern and Manage. The framework
also shows why one high hit@1 is not enough on its own. Independent label checks (#406),
no-match behaviour and source freshness all have to hold before anyone calls the Explainer
reliable.

**12. Carpineto & Romano (2012).**
*Reference.* Carpineto, C., & Romano, G. (2012). A survey of automatic query expansion in
information retrieval. *ACM Computing Surveys, 44*(1), Article 1. https://doi.org/10.1145/2071389.2071390
*Summary.* The survey reviews automatic query expansion. Its abstract describes a short keyword
query as a poor model of the user's need, and expansion as adding terms with a similar meaning.
*Evaluation.* It is a broad, peer-reviewed survey and the standard reference for the method.
Claims about its taxonomy and precision trade-offs are not used until the full text is read
(section 6).
*Application.* The #383 synonym map is manual query expansion. It raised in-sample synonym hit@1
from 0.200 to 1.000, and on the blind held-out set (#390) it scores 0.800, against 0.500 without
the map. Leaving out "log", "baby" and "travel" and scoring expanded terms at half weight
(`_SYNONYM_WEIGHT = 0.5`) were project choices, not findings of this survey.

## References

Bruch, S., Gai, S., & Ingber, A. (2024). An analysis of fusion functions for hybrid retrieval.
*ACM Transactions on Information Systems, 42*(1), Article 20. https://doi.org/10.1145/3596512

Carpineto, C., & Romano, G. (2012). A survey of automatic query expansion in information
retrieval. *ACM Computing Surveys, 44*(1), Article 1. https://doi.org/10.1145/2071389.2071390

Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal rank fusion outperforms
Condorcet and individual rank learning methods. In *Proceedings of the 32nd International ACM
SIGIR Conference on Research and Development in Information Retrieval* (pp. 758-759).
https://doi.org/10.1145/1571941.1572114

Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2024). RAGAs: Automated evaluation of
retrieval augmented generation. In *Proceedings of the 18th Conference of the European Chapter of
the Association for Computational Linguistics: System Demonstrations* (pp. 150–158). Association
for Computational Linguistics. https://doi.org/10.18653/v1/2024.eacl-demo.16

Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., Wang, M., & Wang, H.
(2023). *Retrieval-augmented generation for large language models: A survey* (arXiv:2312.10997).
arXiv. https://doi.org/10.48550/arXiv.2312.10997

Karpukhin, V., Oguz, B., Min, S., Lewis, P., Wu, L., Edunov, S., Chen, D., & Yih, W. (2020).
Dense passage retrieval for open-domain question answering. In *Proceedings of the 2020
Conference on Empirical Methods in Natural Language Processing* (pp. 6769-6781).
https://doi.org/10.18653/v1/2020.emnlp-main.550

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M.,
Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for
knowledge-intensive NLP tasks. In *Advances in Neural Information Processing Systems 33*.
https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html

Manning, C. D., Raghavan, P., & Schütze, H. (2008). *Introduction to information retrieval*.
Cambridge University Press. https://nlp.stanford.edu/IR-book/

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model* (W3C Recommendation).
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/

National Institute of Standards and Technology. (2023). *Artificial intelligence risk management
framework (AI RMF 1.0)* (NIST AI 100-1). https://doi.org/10.6028/NIST.AI.100-1

Robertson, S., & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond.
*Foundations and Trends in Information Retrieval, 3*(4), 333-389.
https://doi.org/10.1561/1500000019

Thakur, N., Reimers, N., Rücklé, A., Srivastava, A., & Gurevych, I. (2021). BEIR: A
heterogeneous benchmark for zero-shot evaluation of information retrieval models. In
*Proceedings of the Neural Information Processing Systems Track on Datasets and Benchmarks*.
https://arxiv.org/abs/2104.08663

## 6. Check against the originals, 14 Oct 2026

Each row was compared with a page or API record opened that day. "Citation" means title,
authors, year, and venue or DOI. Where an abstract or the document text was opened, the claim
in the note was compared with that text.

| # | Record opened | What matched | What did not |
|---|---|---|---|
| 1 | Publisher suggested citation and DOI `10.1561/1500000019` (now publishers, INR-019). Crossref for the same DOI. | Title, authors, year 2009, DOI. Publisher citation is *Foundations and Trends in Information Retrieval*, 3(4), 333-389. | Crossref and the Emerald reissue list the same DOI as volume 4, issues 1-2, pages 1-174. The reference keeps the publisher's own suggested citation. The k1 and b description in section 2.1 was not re-read in the article body. |
| 2 | Authors' site, https://nlp.stanford.edu/IR-book/ | Manning, Raghavan and Schütze, *Introduction to Information Retrieval*, Cambridge University Press, 2008. ISBN 0521865719. Chapter 6 is term weighting and the vector space model. Chapter 8 is evaluation. | The chapter text was not re-read. |
| 3 | Crossref `10.18653/v1/2020.emnlp-main.550`. ar5iv HTML of arXiv:2004.04906. | EMNLP 2020, pages 6769-6781, authors as cited. Abstract: the dense retriever outperforms Lucene-BM25 by 9 to 19 percentage points absolute on top-20 passage retrieval accuracy. | No discrepancy recorded. The paper body was not re-read. |
| 4 | arXiv:2104.08663 PDF and abstract. NeurIPS 2021 Datasets and Benchmarks abstract. | 18 datasets. Abstract: BM25 is a robust baseline, and dense models often underperform other approaches zero-shot. PDF title spelling is "Heterogeneous". | The arXiv landing title spells it "Heterogenous". The reference follows the PDF. |
| 5 | Crossref `10.1145/1571941.1572114`. | SIGIR 2009, pages 758-759. Authors Cormack, Clarke and Büttcher. The title states the comparison with Condorcet fusion. | The paper body was not re-read. Crossref had no abstract. |
| 6 | Crossref `10.1145/3596512`, including the abstract. | *ACM Transactions on Information Systems*, 42(1), Article 20 (35 pp.). Final issue January 2024; some online-first records list 2023. Authors Bruch, Gai and Ingber. Abstract: a convex combination outperforms RRF in in-domain and out-of-domain settings, and RRF is sensitive to its parameters. | The 2023 online-first date and January 2024 final-issue date differ; final issue year used in the reference after 30 Oct reconciliation. Full paper body was not re-read. |
| 7 | NeurIPS 2020 proceedings abstract and the 16-page proceedings PDF. | Authors, title, NeurIPS 2020. Abstract: on generation tasks, RAG produces more specific, diverse and factual language than a parametric-only baseline. | An earlier draft gave pages 9459-9474. Neither the abstract page nor the proceedings PDF prints that span, so the pages were removed. |
| 8 | arXiv:2312.10997 HTML, DataCite DOI `10.48550/arXiv.2312.10997`. | Authors and title match. Headings: Naive RAG, Advanced RAG, Modular RAG. Advanced RAG describes pre-retrieval and post-retrieval steps aimed at retrieval quality. | "Retrieval quality is the main lever on answer quality" was not in the text that was opened. It is removed from section 2.4 and note 8. |
| 9 | **26 Oct follow-up:** ACL Anthology https://aclanthology.org/2024.eacl-demo.16/ bibliographic record and abstract; previous 14 Oct arXiv metadata retained as history. | Peer-reviewed EACL 2024 System Demonstrations paper, pp. 150–158, DOI `10.18653/v1/2024.eacl-demo.16`, by the four named authors. The abstract supports a reference-free framework assessing retrieval/context and generation quality. | The older draft treated only the 2023 arXiv preprint as the final venue. Corrected the source and in-text year to 2024. Full proceedings paper not re-read on 26 Oct; claims beyond the abstract remain bounded. |
| 10 | https://www.w3.org/TR/prov-dm/ | W3C Recommendation, 30 April 2013. Editors Luc Moreau and Paolo Missier. The text defines entities, activities and agents, and uses `wasDerivedFrom` and `wasAttributedTo`. | No discrepancy recorded. |
| 11 | PDF at https://doi.org/10.6028/NIST.AI.100-1 | NIST AI 100-1, January 2023. The core functions are Govern, Map, Measure and Manage. "Valid and reliable" and "accountable and transparent" are named characteristics. | Crossref lists Elham Tabassi as author. The PDF cover names NIST. The reference keeps the institutional author, which is what the cover shows. |
| 12 | Crossref `10.1145/2071389.2071390`, including the abstract. | *ACM Computing Surveys*, 44(1), 1-50, 2012. Authors Carpineto and Romano. The abstract is a survey of automatic query expansion. | The abstract does not give the four method groups, and it does not say expansion hurts precision by drifting. Those claims are withdrawn in note 12 and in section 4 until the article body is read. |


## 7. Original-source follow-up, 26 Oct 2026

The citations below are a documented second check of accessible **publisher or canonical
record/abstract pages** on 26 Oct. These are not claims to have read the full copyrighted
paper bodies; section 6 still records the scope of the first check. At least eight of
the twelve references are peer-reviewed papers or peer-reviewed research monographs:
Robertson & Zaragoza, Karpukhin et al., Thakur et al., Cormack et al., Bruch et al.,
Lewis et al., Es et al. (now EACL 2024), and Carpineto & Romano. Manning et al. is a
textbook; W3C PROV-DM and NIST AI RMF are standards/frameworks, and Gao et al. is
retained as a preprint survey rather than misrepresented as a peer-reviewed journal.

| Source | Accessible record opened on 26 Oct | Check and bound |
|---|---|---|
| Manning et al. (2008) | https://www.cambridge.org/highereducation/books/introduction-to-information-retrieval/669D108D20F556C5C30957D63B5AB65C | The publisher lists chapter 6 for term weighting and chapter 8 for evaluation; no fresh close-reading of either chapter |
| Karpukhin et al. (2020) | https://aclanthology.org/2020.emnlp-main.550/ | ACL Anthology confirms authors, EMNLP venue, pp. 6769–6781 and abstract's 9–19 percentage-point top-20 retrieval advantage *on tested QA datasets*, not on INZBC |
| Thakur et al. (2021) | https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/65b9eea6e1cc6bb9f0cd2a47751a186f-Abstract-round2.html | NeurIPS abstract confirms 18 datasets, BM25 as a robust general baseline, and many zero-shot dense models underperforming; no assertion this transfers to INZBC |
| Cormack et al. (2009) | https://dl.acm.org/doi/10.1145/1571941.1572114 | ACM confirms SIGIR 2009, pp. 758–759 and ranking-fusion claim; no fresh full-paper review or claim of an optimal k on INZBC |
| Bruch et al. (2024) | https://arxiv.org/abs/2210.11934 | Abstract corroborates the comparison of convex score fusion and RRF, including RRF parameter sensitivity and the small labelled sample needed for score-fusion tuning; the cited *journal* is still the authoritative venue |
| Gao et al. (2023) | https://arxiv.org/abs/2312.10997 | Abstract confirms naive, advanced and modular RAG taxonomy; no attribution of unsupported 'main lever' claim |
| Es et al. (2024) | https://aclanthology.org/2024.eacl-demo.16/ | **Correction:** peer-reviewed EACL 2024 demonstration, pp. 150–158; original 2023 arXiv record was not the final paper citation |
| W3C PROV-DM (2013) | https://www.w3.org/TR/prov-dm/ | Official Recommendation names entities, activities and agents; this does not mean INZBC has implemented full PROV-DM lineage |
| Carpineto & Romano (2012) | https://doi.org/10.1145/2071389.2071390 | Previously verified publisher/Crossref citation; the abstract establishes the concept of query expansion but does not substantiate a numeric precision or 'query drift' claim for our map |

**Remaining evidence limits:** Full text for Robertson & Zaragoza, Cormack et al.,
Bruch et al. and Carpineto & Romano was not re-read in this 26 Oct session.
Robertson & Zaragoza's publisher-suggested first citation (3(4), 333–389) and the
later Emerald/DOI page's 4(1–2), 1–174 display are still a known bibliographic
discrepancy; the reference retains the originally verified citation instead of
quietly choosing a new one. Lewis et al. (2020) and NIST (2023) retain the earlier
14 Oct proceedings/PDF verification in section 6, not a fabricated 26 Oct review.

**Interpretation for INZBC:** None of these external publications supplies a
valid measured dense/hybrid accuracy figure or a score threshold for our
22 confirmed FTA entries (out of 23 total). Those must come from #393's controlled experiments,
independently checked labels and the tech lead's subsequent decision.

## 6A. Original-text spot verification, 30 Oct 2026

These checks add **passage-level evidence**, not a claim that all twelve full texts
were reread or that a new retrieval experiment occurred. Historic checks and
limitations in section 6 remain intact.

| Source | Original text checked today | Supported claim and boundary |
|---|---|---|
| Robertson & Zaragoza (2009), https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf | Author-hosted monograph, section 3.4.2 p. 356 and section 3.4.5 p. 359 | Section 3.4.2 explicitly describes diminishing term-frequency contribution as *saturation*. Section 3.4.5 derives document-length soft normalisation relative to the average length and the parameter `b`. This verifies the **mechanism** described in section 2.1, not BM25's performance on INZBC's corpus. The original front matter prints *Foundations and Trends in Information Retrieval* 3(4), 333–389; the Emerald reissue presents 4(1–2), 1–174 under the same DOI. |
| Cormack, Clarke & Büttcher (2009), https://cormack.uwaterloo.ca/cormack/cormacksigir09-rrf.pdf | Authors' two-page SIGIR paper, pp. 758–759 | Section 1 defines `RRFscore(d) = sum(1 / (k + rank(d)))`, with `k=60` fixed after pilot selection. It combines rankings, not comparable raw scores. The paper compares RRF on TREC and LETOR 3; results are **not** evidence that RRF improves this project's 23-entry FTA corpus. In its TREC comparisons there are exceptions (e.g., CombMNZ on TREC 3), so do not claim universal dominance. |

Additional bibliographic reconciliation (30 Oct): DBLP's journal-volume record
and the IR Anthology list Bruch, Gai and Ingber as *42*(1), Article 20,
35 pages, in the **January 2024 issue**; the 2023 online-first
version is preserved here as a date distinction, not silently treated
as a different paper (DOI `10.1145/3596512`). The journal-issue year
**2024** is used consistently for the final-issue APA-style reference.
For Carpineto and Romano the original ACM reference format says
*44*(1), **Article 1**, 50 pages (DOI `10.1145/2071389.2071390`).
Neither record check proves an additional scientific claim from the
unread full paper.

The Stanford textbook chapter body, other full papers, and any additional passages
not explicitly named above **were not verified in this follow-up**. The original
12-source citation/abstract checks and the existing issue #387 acceptance review
remain separately documented; no new client or human evaluation was performed.
