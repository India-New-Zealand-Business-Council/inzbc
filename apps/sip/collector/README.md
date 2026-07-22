# apps/sip/collector — integration with the collection agent

Owner: Roshan. Maps the `daily-india-nz-news-agent` repo's output onto
`apps/sip/pipeline`'s `Candidate` model, then writes it into an existing run via
`apps/sip/pipeline/client.py`.

- `mapping.py` — `map_article()`/`map_articles()`: turns one of `agent.py`'s `clean_articles()`
  output dicts into a `Candidate` (SIP-184 step 5, raw capture only — no scoring, verification,
  duplicate or routing decisions; those are later SOP steps). Read from the actual agent source
  in `india-new-zealand-business-council/daily-india-nz-news-agent`, not an assumed schema.
- `ingest.py` — `ingest_articles()`: maps a batch and POSTs each to `/api/candidates` via
  `SipPipelineClient.create_candidate`, collecting per-item failures instead of aborting the
  batch on the first one.
- `source_register.py` — SIP-185's mandatory source worklist (`MANDATORY_SOURCES`), the fallback
  sequence, `missing_mandatory_outcomes()` (client-side check mirroring SIP-184's "blank
  mandatory-source outcome is a Critical stop"), and `record_source_outcome()` to build a
  `SourceCheck` per source, folding a fallback-attempt trail into `notes` since the table has no
  separate attempts column.
- `tests/` — local checks against fixture article dicts and a fake client; no live agent or API
  needed.

## Known gap: source_id resolution
Both the agent's articles and SIP-185's source register only give a free-text source name (e.g.
`"RNZ Business"`, `"MFAT"`); there is no `source_library` lookup endpoint in
`schemas/api-contract.md` yet to resolve a name to its DB id.
- `map_article`/`map_articles`/`ingest_articles` take an optional `source_lookup: dict[str,
  str]` (name → id); candidates write with `source_id=None` when a name doesn't resolve —
  `candidates.source_id` is nullable, so this is a degraded-but-valid write.
- `record_source_outcome()` requires `source_lookup` to resolve the name and raises
  `SourceIdUnresolved` if it doesn't — `source_checks.source_id` is **NOT NULL**
  (`database/schema.sql`), so there is no valid source check without one; this can't degrade
  gracefully the way candidate capture can.
Tracked in `docs/workstreams/roshan.md`'s blocked list — a contract change needs Bhanu.

## Still blocked
- **Live runs.** Collection-engine secrets (`OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, etc.) aren't
  supplied here, and `services/api` is still a stub — nothing in this module can be exercised
  end-to-end yet, only unit-tested against fixtures. Wire `ingest_articles()` to a real run once
  both exist: create the run via `SipPipelineClient.create_run`, call
  `agent.clean_articles(agent.fetch_news(24))` (or however the agent's `main()` is refactored to
  expose that list), then `ingest_articles(client, run_id, articles)`.
