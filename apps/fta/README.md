# apps/fta — FTA Implementation Centre + Explainer service

Owner: Roshan. Corpus: `docs/fta-source-corpus.md`. See `docs/modules/fta-centre.md`.
Sourced answers only (Tier 1 citations + effective dates). UI embed: Paras (`apps/fta/ui`).

- `corpus.py` — structured mirror of `docs/fta-source-corpus.md`: `TIER_1_SOURCES`/
  `TIER_2_SOURCES` (with the two India-side documents flagged
  `automated_fetch_blocked=True`), `CORPUS` (one `TariffOutcome` per sourced fact, each carrying
  its own `confirmed` flag and citation so an unconfirmed figure — e.g. the ~70% tariff-line
  count — can never be presented as settled), and `stale_entries()` for freshness tracking.
  `SECTORS_IN_SCOPE` lists the tariff-outcome categories built now (settled 9 Aug 2026, #219 —
  see the constant's docstring); it grows as "add next" sectors (tourism, education, investment)
  get sourced, not on further INZBC confirmation. Update `docs/fta-source-corpus.md` first, then
  mirror the change here — that doc is the
  controlling reference, same relationship `apps/sip/collector/source_register.py` has to
  SIP-185.
- `explainer.py` — `answer_query()`: matches a sector/product query against the corpus by shared
  keyword and returns each match as an `ExplainerAnswer` (treatment, status line, jurisdiction,
  citation, effective/verified date, next step, disclaimer). No model call — matching is
  keyword-only, so there is nothing here to hallucinate a fact. Returns `[]` on no match (or an
  empty/stopword-only query) — the caller routes that to INZBC rather than guessing, per
  `docs/modules/fta-centre.md`'s "unsupported-answer behaviour" requirement.

## Disclaimer + confidence (resolved 24 Jul 2026)
Every answer now carries the INZBC AI Information Standard as its disclaimer plus an
Information Confidence Standard rating — approved wording from Sunil Kaushal (CEO), canonical
in `docs/information-standard.md`, mirrored in `standards.py`. Confidence derives from the
cited source's tier (`TariffOutcome.source_tier`): Tier 1 official → High, Tier 2
industry/secondary → Medium; unconfirmed entries stay suppressed, and the `[]` no-match path
is surfaced as **Action Required** (`explainer.NO_MATCH_CONFIDENCE`).

## Known gap: freshness re-verification
`stale_entries()` only flags entries by how long ago they were last verified — it cannot check
whether MFAT/PIB/Dept of Commerce pages have actually changed since, since that needs either a
scheduled fetch-and-diff job (an infrastructure decision, not made yet) or a person re-reading
the source. It also takes `review_after_days` with no default — the review cadence is a business
decision `docs/modules/fta-centre.md` still lists as an open dependency (the legal/technical
review process), not something to assume here.
