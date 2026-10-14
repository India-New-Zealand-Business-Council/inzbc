# Literature review: retrieval for governed AI

**Author:** Roshan Aryal. **Status:** Draft, started 13 Oct 2026. Bibliographic record of all
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
| Must return no match | 6 | no-match accuracy 1.000 | |

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
adds little, and long documents are normalised so they do not win on length alone. That account
was not re-read in the 2009 article on 14 Oct (section 6). Manning et al. (2008) cover the
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
need calibrating. Bruch et al. (2023) compared fusion functions and found that a convex
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
is what `apps/fta/eval/` reports. RAGAS (Es et al., 2023) proposes reference-free scores for a
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
| Keyword TF-IDF (today) | Shared terms weighted by rarity | Transparent, no dependencies, exact wording 1.000 | No match without a shared word. Synonyms 0.200 | Good floor. Keep it |
| BM25 | TF-IDF with saturation and length normalisation. That account of the 2009 article was not re-read on 14 Oct (section 6) | Robust zero-shot baseline (BEIR abstract) | Same vocabulary gap. A rare framing word can outweigh the product | Measured worse (#398): 0.333 hit@1 on product plus framing questions, where "exports" outweighs "dairy" |
| Keyword plus synonym list | Expand the query with terms of a similar meaning (Carpineto & Romano, 2012) | Explainable, no model call, cheap to test | The list has to be maintained by hand, and misses terms nobody listed. On this corpus an ambiguous added term can point at another topic. That limit is from #383, not from the survey abstract | Built (#383). Synonym hit@1 0.200 to 1.000, no-match unchanged |
| Dense embeddings | Rank by vector similarity | Matches meaning, so it handles synonyms | Zero-shot reliability (BEIR). Needs a model, which may cross the model data boundary in ADR-0006 | Possible, but must not lose an exact or no-match result |
| Hybrid (RRF) | Fuse lexical and dense rankings | Keeps exact matches and adds semantic recall | Two systems to run. A similarity cut-off is needed or no-match questions start returning answers | Best candidate if embeddings are approved under #63 |

The deciding risk for INZBC is not the miss but the false answer. A dense retriever always
returns its nearest neighbour, even for "steel" or "pharmaceuticals", which the corpus does not
cover. Today those return no match and route to INZBC (no-match accuracy 1.000). Any change has
to keep that, which means a similarity threshold, tuned and checked on the six no-match
questions.

## 4. What this means for the project

1. **Measure first.** Done (#382). The set has since grown to 52 questions.
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
4. **Then embeddings under #63**, if Bhanu agrees and the model data boundary allows it. The
   design would be hybrid with RRF, plus a similarity threshold so no-match questions stay
   unanswered.
5. **Report all variants in one table** (keyword, keyword plus synonyms, embeddings, hybrid), by
   question type, in W7.
6. **What does not apply:** training a DPR model (no labelled pairs, and 23 entries do not
   justify it), and RAG generation for FTA answers (the Explainer must quote the corpus, not
   paraphrase it).

## 5. Annotated bibliography

Each entry needs about 150 words in four parts: reference, summary, evaluation, application to
INZBC. Expand each first-pass note below into a full annotation by 30 Oct.

| # | Source | Type | Checked against original | Annotation done |
|---|---|---|---|---|
| 1 | Robertson & Zaragoza (2009) | Peer-reviewed | 14 Oct 2026, citation | |
| 2 | Manning, Raghavan & Schütze (2008) | Textbook | 14 Oct 2026, citation | |
| 3 | Karpukhin et al. (2020) | Peer-reviewed | 14 Oct 2026, citation and abstract | |
| 4 | Thakur et al. (2021) | Peer-reviewed | 14 Oct 2026, citation and abstract | |
| 5 | Cormack, Clarke & Büttcher (2009) | Peer-reviewed | 14 Oct 2026, citation | |
| 6 | Bruch, Gai & Ingber (2023) | Peer-reviewed | 14 Oct 2026, citation and abstract | |
| 7 | Lewis et al. (2020) | Peer-reviewed | 14 Oct 2026, citation and abstract | |
| 8 | Gao et al. (2023) | Preprint survey | 14 Oct 2026, citation and section headings | |
| 9 | Es et al. (2023) | Preprint | 14 Oct 2026, citation and terms | |
| 10 | Moreau & Missier (2013) | Standard | 14 Oct 2026, recommendation text | |
| 11 | NIST (2023) | Framework | 14 Oct 2026, PDF | |
| 12 | Carpineto & Romano (2012) | Peer-reviewed survey | 14 Oct 2026, citation and abstract | |

### First-pass notes

Started 14 Oct to speed up the annotations. Each note gives the claim, a first evaluation and the
link to INZBC. The citation check is in section 6. These notes still have to be rewritten as
full annotations before 30 Oct. They are not that yet.

**1. Robertson & Zaragoza (2009).** The monograph on the probabilistic relevance framework and
BM25, by the method's authors. *Evaluate:* the standard reference for BM25. Citation checked
against the publisher's suggested citation. The article body was not re-read on 14 Oct, so the
k1 and b description is not marked as checked (section 6). *Apply:* implemented in #398.
With three to eight tokens per entry, length normalisation has almost nothing to work on, and IDF
on a rare framing word hurt product questions. That result is from #398, not from this monograph.

**2. Manning, Raghavan & Schütze (2008).** The standard textbook on TF-IDF weighting, the vector
space model and how to evaluate ranked retrieval. *Evaluate:* a textbook, not new research, but
the accepted reference for the basics. *Apply:* the live ranker's IDF weighting and the eval's
ranked metrics come from these ideas.

**3. Karpukhin et al. (2020).** Dense Passage Retrieval trains two BERT encoders on question and
passage pairs and beats BM25 on top-20 retrieval accuracy on several open-domain QA sets.
*Evaluate:* strong results, but in-domain and with large labelled training data. *Apply:* INZBC
has no labelled pairs and 23 entries, so training a retriever is out. Only a pre-trained model
used zero-shot is realistic.

**4. Thakur et al. (2021).** BEIR tests retrievers zero-shot across 18 datasets. BM25 is a robust
baseline, and many dense models do worse outside the domain they were trained on. *Evaluate:* a
broad benchmark, so its conclusions are general. #398 found one case where they do not hold for a
tiny corpus. *Apply:* a warning for #63. An embedding model has to beat the live ranker on our
questions, not on BEIR.

**5. Cormack, Clarke & Büttcher (2009).** Reciprocal Rank Fusion combines several rankings using
only each item's rank, and beat the individual methods and Condorcet fusion in their TREC tests.
*Evaluate:* a short paper, but simple and widely reused. *Apply:* the obvious way to combine the
live ranker with an embedding ranker under #393, because it needs no score calibration.

**6. Bruch, Gai & Ingber (2023).** Compares fusion functions for hybrid retrieval and finds that a
convex combination of normalised scores can beat RRF, which is sensitive to its own parameter.
*Evaluate:* careful and recent, but the gain needs some tuning data. *Apply:* with 52 questions,
tuning weights risks fitting the eval set, so RRF is the safer first try.

**7. Lewis et al. (2020).** Retrieval-augmented generation joins a dense retriever to a generator,
so answers are written from retrieved passages. On generation tasks the paper reports more
specific, diverse and factual language than a parametric-only baseline. *Evaluate:* the paper
that named RAG. Checked against the NeurIPS 2020 abstract page. *Apply:* the retrieval half
applies directly. The generation half does not apply to FTA answers, which quote the corpus.

**8. Gao et al. (2023).** Surveys RAG since Lewis et al. and groups systems into naive, advanced
and modular RAG. Advanced RAG is where the survey puts pre-retrieval and post-retrieval work.
*Evaluate:* a preprint survey, useful for structure, not as evidence for any single experiment.
An earlier note said retrieval quality is the main lever on answer quality. That sentence is
not in the survey text that was opened, so it is dropped. *Apply:* the grouping is a map of the
field. The decision to measure retrieval first comes from the FTA baseline, not from this paper.

**9. Es et al. (2023).** RAGAS scores a RAG pipeline without reference answers: faithfulness,
answer relevance and context relevance, each judged by a language model. *Evaluate:* a preprint,
and the scores depend on the judging model. *Apply:* relevant to #64 (judging brief quality), not
to FTA answers, where a hand-labelled question set is cheaper and more trustworthy.

**10. Moreau & Missier (2013).** PROV-DM models provenance as entities, the activities that used
or produced them, and the agents responsible. *Evaluate:* a W3C standard, so authoritative but
abstract. *Apply:* each corpus entry's citation, tier and verified date is provenance already.
PROV gives it standard names.

**11. NIST (2023).** The AI Risk Management Framework organises AI risk work into Govern, Map,
Measure and Manage, and lists "valid and reliable" among the marks of trustworthy AI.
*Evaluate:* a government framework, not research, but widely adopted. *Apply:* the committed
eval and the CI gate (#394) are the Measure function in practice.

**12. Carpineto & Romano (2012).** Surveys automatic query expansion. The abstract says a short
keyword query is a poor model of the need, and that expansion adds features with a similar
meaning. *Evaluate:* a broad, peer-reviewed survey, and the standard reference for this method.
The abstract does not list thesaurus, corpus, query-log and relevance-feedback methods, and it
does not say expansion hurts precision when it drifts. Those two sentences were in the 14 Oct
note and are withdrawn until the paper body is read. *Apply:* the synonym map is manual
expansion, which is in scope for this survey. Leaving out "log", "baby" and "travel", and scoring
expanded terms at half weight, was a project choice on #383. It is not a result quoted from this
paper.

## References

Bruch, S., Gai, S., & Ingber, A. (2023). An analysis of fusion functions for hybrid retrieval.
*ACM Transactions on Information Systems, 42*(1), 1-35. https://doi.org/10.1145/3596512

Carpineto, C., & Romano, G. (2012). A survey of automatic query expansion in information
retrieval. *ACM Computing Surveys, 44*(1), 1-50. https://doi.org/10.1145/2071389.2071390

Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal rank fusion outperforms
Condorcet and individual rank learning methods. In *Proceedings of the 32nd International ACM
SIGIR Conference on Research and Development in Information Retrieval* (pp. 758-759).
https://doi.org/10.1145/1571941.1572114

Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2023). *Ragas: Automated evaluation of
retrieval augmented generation* (arXiv:2309.15217). arXiv. https://doi.org/10.48550/arXiv.2309.15217

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
| 3 | Crossref `10.18653/v1/2020.emnlp-main.550`. ar5iv HTML of arXiv:2004.04906. | EMNLP 2020, pages 6769-6781, authors as cited. Abstract: the dense retriever outperforms Lucene-BM25 by 9 to 19 percentage points absolute on top-20 passage retrieval accuracy. | |
| 4 | arXiv:2104.08663 PDF and abstract. NeurIPS 2021 Datasets and Benchmarks abstract. | 18 datasets. Abstract: BM25 is a robust baseline, and dense models often underperform other approaches zero-shot. PDF title spelling is "Heterogeneous". | The arXiv landing title spells it "Heterogenous". The reference follows the PDF. |
| 5 | Crossref `10.1145/1571941.1572114`. | SIGIR 2009, pages 758-759. Authors Cormack, Clarke and Büttcher. The title states the comparison with Condorcet fusion. | The paper body was not re-read. Crossref had no abstract. |
| 6 | Crossref `10.1145/3596512`, including the abstract. | *ACM Transactions on Information Systems*, 42(1), 1-35, 2023. Authors Bruch, Gai and Ingber. Abstract: a convex combination outperforms RRF in in-domain and out-of-domain settings, and RRF is sensitive to its parameters. | |
| 7 | NeurIPS 2020 proceedings abstract and the 16-page proceedings PDF. | Authors, title, NeurIPS 2020. Abstract: on generation tasks, RAG produces more specific, diverse and factual language than a parametric-only baseline. | An earlier draft gave pages 9459-9474. Neither the abstract page nor the proceedings PDF prints that span, so the pages were removed. |
| 8 | arXiv:2312.10997 HTML, DataCite DOI `10.48550/arXiv.2312.10997`. | Authors and title match. Headings: Naive RAG, Advanced RAG, Modular RAG. Advanced RAG describes pre-retrieval and post-retrieval steps aimed at retrieval quality. | "Retrieval quality is the main lever on answer quality" was not in the text that was opened. It is removed from section 2.4 and note 8. |
| 9 | DataCite DOI `10.48550/arXiv.2309.15217`. arXiv HTML. | Authors Es, James, Espinosa-Anke and Schockaert. The paper's title is "Ragas", not "RAGAS". The HTML uses faithfulness, answer relevance and context relevance. | The reference title now follows the paper. |
| 10 | https://www.w3.org/TR/prov-dm/ | W3C Recommendation, 30 April 2013. Editors Luc Moreau and Paolo Missier. The text defines entities, activities and agents, and uses `wasDerivedFrom` and `wasAttributedTo`. | |
| 11 | PDF at https://doi.org/10.6028/NIST.AI.100-1 | NIST AI 100-1, January 2023. The core functions are Govern, Map, Measure and Manage. "Valid and reliable" and "accountable and transparent" are named characteristics. | Crossref lists Elham Tabassi as author. The PDF cover names NIST. The reference keeps the institutional author, which is what the cover shows. |
| 12 | Crossref `10.1145/2071389.2071390`, including the abstract. | *ACM Computing Surveys*, 44(1), 1-50, 2012. Authors Carpineto and Romano. The abstract is a survey of automatic query expansion. | The abstract does not give the four method groups, and it does not say expansion hurts precision by drifting. Those claims are withdrawn in note 12 and in section 4 until the article body is read. |
