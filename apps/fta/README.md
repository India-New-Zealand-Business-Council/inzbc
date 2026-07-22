# apps/fta — FTA Implementation Centre + Explainer service

Owner: Roshan. Corpus: `docs/fta-source-corpus.md`. See `docs/modules/fta-centre.md`.
Sourced answers only (Tier 1 citations + effective dates). UI embed: Paras (`apps/fta/ui`).

- `corpus.py` — structured mirror of `docs/fta-source-corpus.md`: `TIER_1_SOURCES`/
  `TIER_2_SOURCES` (with the two India-side documents flagged
  `automated_fetch_blocked=True`), `CORPUS` (one `TariffOutcome` per sourced fact, each carrying
  its own `confirmed` flag and citation so an unconfirmed figure — e.g. the ~70% tariff-line
  count — can never be presented as settled), and `stale_entries()` for freshness tracking.
  `PROVISIONAL_SECTORS_IN_SCOPE` mirrors the doc's tentative sector list, marked provisional.
  Update `docs/fta-source-corpus.md` first, then mirror the change here — that doc is the
  controlling reference, same relationship `apps/sip/collector/source_register.py` has to
  SIP-185.

## Known gap: freshness re-verification
`stale_entries()` only flags entries by how long ago they were last verified — it cannot check
whether MFAT/PIB/Dept of Commerce pages have actually changed since, since that needs either a
scheduled fetch-and-diff job (an infrastructure decision, not made yet) or a person re-reading
the source. It also takes `review_after_days` with no default — the review cadence is a business
decision `docs/modules/fta-centre.md` still lists as an open dependency (INZBC sectors-in-scope +
disclaimer + legal/technical review process), not something to assume here.
